"""Server-side PDF report generation.

Produces a professional, deterministic, single-page-plus PDF from an analysis
evidence packet (ML detection + severity + flow indicators + retrieved MITRE
context + optional LLM explanation).

Security guarantees:
- All user-controlled text passes through sanitize_text() / sanitize_paragraph()
  (strip control chars, force ASCII, XML-escape for Paragraph markup).
- Report filenames are server-generated UUIDs; the endpoint never accepts a
  path. report_file() validates the report id as 32-hex and resolves strictly
  inside the configured output directory.
- No API keys / environment variables / credentials are ever rendered. Only
  explicit evidence fields make it into the document.
- Generation fails safely: rendering or IO errors become ReportGenerationException.
"""
import io
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings
from app.core.exceptions import (
    ReportGenerationException,
    ReportNotFoundException,
)
from app.core.logging import get_logger
from app.schemas.llm import LLMExplanationOutput
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.analysis_evidence import AnalysisEvidence
from app.services.llm_prompts import summarize_flow

logger = get_logger("report_service")

_REPORT_ID_RE = re.compile(r"^[0-9a-f]{32}$")

_REPLACEMENTS = {
    "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-",
    "\u2026": "...", "\u00a0": " ",
}


def sanitize_text(value: Any, max_len: int = 2000) -> str:
    """Strip control/non-ASCII characters; safe for drawString/filename use."""
    if value is None:
        return ""
    s = str(value)
    s = "".join(ch for ch in s if ch in ("\n", "\t") or ord(ch) >= 32)
    for k, v in _REPLACEMENTS.items():
        s = s.replace(k, v)
    s = "".join(ch if ord(ch) < 256 else "?" for ch in s)
    return s[:max_len]


def sanitize_paragraph(value: Any, max_len: int = 4000) -> str:
    """Sanitize + XML-escape so user text cannot inject reportlab markup."""
    return xml_escape(sanitize_text(value, max_len))


@dataclass
class ReportSectionTechnique:
    technique_id: str
    technique_name: str
    score: float
    tactics: List[str] = field(default_factory=list)
    description: str = ""
    mitigations: List[str] = field(default_factory=list)
    technique_type: str = "technique"


@dataclass
class ReportContent:
    app_name: str
    report_type: str
    report_id: str
    request_id: str
    generated_at_display: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    experiment_id: str
    operating_point: str
    model_version: str
    severity_level: str
    risk_score: float
    calibration_note: str
    indicators: Dict[str, Any] = field(default_factory=dict)
    techniques: List[ReportSectionTechnique] = field(default_factory=list)
    explanation: Optional[LLMExplanationOutput] = None


class PdfReportRenderer:
    """Renders ReportContent to a PDF byte string using reportlab."""

    def __init__(self) -> None:
        _base = getSampleStyleSheet()
        title = ParagraphStyle(
            "ReportTitle", parent=_base["Title"], fontSize=17, leading=21,
            spaceAfter=2, textColor=colors.HexColor("#1F3B57"),
        )
        self.subtitle = ParagraphStyle(
            "ReportSubtitle", parent=_base["Normal"], fontSize=9, leading=12,
            textColor=colors.HexColor("#666666"), spaceAfter=6,
        )
        self.h2 = ParagraphStyle(
            "SectionTitle", parent=_base["Heading2"], fontSize=12.5, leading=15,
            spaceBefore=12, spaceAfter=5, textColor=colors.HexColor("#1F3B57"),
            alignment=TA_LEFT,
        )
        self.body = ParagraphStyle(
            "Body", parent=_base["Normal"], fontSize=9.5, leading=13, spaceAfter=4,
        )
        self.small = ParagraphStyle(
            "Small", parent=_base["Normal"], fontSize=8, leading=11,
            textColor=colors.HexColor("#555555"),
        )
        self.cell = ParagraphStyle(
            "Cell", parent=_base["Normal"], fontSize=8.5, leading=11,
        )
        self.cell_header = ParagraphStyle(
            "CellHeader", parent=self.cell, fontName="Helvetica-Bold",
            textColor=colors.white,
        )
        self.technique_name = ParagraphStyle(
            "TechniqueName", parent=self.body, fontName="Helvetica-Bold",
        )
        self._title_style = title

    def render(self, content: ReportContent) -> bytes:
        buffer = io.BytesIO()
        app_footer = sanitize_text(content.app_name, 80)
        ts_footer = sanitize_text(content.generated_at_display, 40)

        def _footer(canvas_obj, doc):
            canvas_obj.saveState()
            canvas_obj.setFont("Helvetica", 8)
            canvas_obj.setFillColor(colors.HexColor("#888888"))
            canvas_obj.drawString(36, 24, f"Generated: {ts_footer} UTC")
            canvas_obj.drawString(36, 12, app_footer)
            canvas_obj.drawRightString(A4[0] - 36, 24, f"Page {doc.page}")
            canvas_obj.restoreState()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36, rightMargin=36, topMargin=44, bottomMargin=44,
            title=sanitize_text(f"{content.app_name} - Analysis Report", 200),
            author=sanitize_text(content.app_name, 200),
            subject="Network anomaly analysis report",
        )
        story = self._build_story(content)
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buffer.getvalue()

    # ------------------------------------------------------------------ #
    # Story building
    # ------------------------------------------------------------------ #
    def _build_story(self, content: ReportContent) -> List[Any]:
        story: List[Any] = []

        story.append(Paragraph(sanitize_paragraph(content.app_name), self._title_style))
        story.append(Paragraph(
            "Network Anomaly Analysis Report",
            ParagraphStyle(
                "ReportKind", parent=self._title_style, fontSize=12, leading=15,
                textColor=colors.HexColor("#B03A2E") if content.is_anomaly else colors.HexColor("#21815B"),
            ),
        ))
        story.append(Paragraph(
            f"Report ID: {sanitize_text(content.report_id)}"
            f" &nbsp;|&nbsp; Request ID: {sanitize_text(content.request_id)}"
            f" &nbsp;|&nbsp; Type: {sanitize_text(content.report_type)}"
            f" &nbsp;|&nbsp; Generated: {sanitize_text(content.generated_at_display)} UTC",
            self.subtitle,
        ))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1F3B57")))

        story.append(Paragraph("Report Metadata", self.h2))
        story.append(self._kv_table([
            ("Report ID", content.report_id),
            ("Request / Analysis ID", content.request_id),
            ("Report Type", content.report_type),
            ("Application", sanitize_text(content.app_name)),
            ("Generated (UTC)", content.generated_at_display),
        ]))

        story.append(Paragraph("Detection Summary", self.h2))
        status = "ANOMALOUS" if content.is_anomaly else "BENIGN"
        story.append(self._kv_table([
            ("Anomaly Status", status),
            ("Anomaly Score", f"{content.anomaly_score:.6f}"),
            ("Operating Threshold", f"{content.threshold:.6f}"),
            ("Experiment / Operating Point", f"{sanitize_text(content.experiment_id)} / {sanitize_text(content.operating_point)}"),
            ("Severity Level", sanitize_text(content.severity_level)),
            ("Risk Score", f"{content.risk_score:.4f}"),
            ("Model Version", sanitize_text(content.model_version)),
        ]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Interpretation.</b> {sanitize_paragraph(self._interpretation(content))}", self.body))

        story.append(Paragraph("Observed Network Indicators", self.h2))
        indicator_rows = self._flatten_indicators(content.indicators)
        if indicator_rows:
            story.append(Paragraph(
                "Selected flow features as computed by the analysis pipeline. Values are reported "
                "from the supplied flow and are not externally validated.",
                self.small,
            ))
            story.append(Spacer(1, 4))
            story.append(self._kv_table([(sanitize_text(k), self._fmt_value(v)) for k, v in indicator_rows], col2=95 * mm))
        else:
            story.append(Paragraph("No indicator data was available for this analysis.", self.body))

        story.append(Paragraph(sanitize_paragraph("MITRE ATT&CK Context"), self.h2))
        story.append(Paragraph(
            "<b>Important:</b> The techniques below were retrieved from the local MITRE ATT&amp;CK "
            "knowledge base as <i>contextual candidates</i> based on flow characteristics. They are "
            "<b>retrieved-not-confirmed</b> evidence and do <b>not</b> constitute a confirmed attack "
            "or attribution.",
            self.body,
        ))
        story.append(Spacer(1, 4))
        if content.techniques:
            story.append(Paragraph(
                f"{len(content.techniques)} candidate technique(s) retrieved.", self.small))
            story.append(Spacer(1, 4))
            story.append(self._technique_table(content.techniques))
            for t in content.techniques:
                story.append(Spacer(1, 6))
                story.append(Paragraph(
                    f"{sanitize_text(t.technique_id)} - {sanitize_paragraph(t.technique_name)}",
                    self.technique_name,
                ))
                if t.description:
                    story.append(Paragraph(sanitize_paragraph(t.description), self.body))
                if t.mitigations:
                    story.append(Paragraph("<b>Mitigations:</b>", self.body))
                    for m in t.mitigations:
                        story.append(Paragraph(f"&bull; {sanitize_paragraph(m)}", self.body))
                else:
                    story.append(Paragraph("No specific mitigations are available.", self.small))
        else:
            story.append(Paragraph(
                sanitize_paragraph(
                    "No MITRE ATT&CK context was retrieved for this analysis "
                    "(RAG unavailable or no relevant candidates)."
                ),
                self.body,
            ))

        story.append(Paragraph("LLM Explanation", self.h2))
        if content.explanation is not None:
            story.extend(self._llm_block(content.explanation))
            story.append(Paragraph(
                "The LLM explanation is generative and explanatory. It is not verified "
                "attribution, diagnosis, or confirmation of any attack technique.",
                self.small,
            ))
        else:
            story.append(Paragraph(
                "No LLM explanation was available for this analysis (LLM disabled or no explanation "
                "was provided). This does not affect the detection evidence above.",
                self.body,
            ))

        story.append(Paragraph("Limitations &amp; Disclaimer", self.h2))
        for line in self._disclaimer_lines():
            story.append(Paragraph(f"&bull; {sanitize_paragraph(line)}", self.body))

        return story

    def _llm_block(self, exp: LLMExplanationOutput) -> List[Any]:
        block: List[Any] = []
        block.append(Paragraph(f"<b>Summary.</b> {sanitize_paragraph(exp.summary)}", self.body))
        block.append(Paragraph(f"<b>Anomaly Assessment.</b> {sanitize_paragraph(exp.anomaly_assessment)}", self.body))
        if exp.observed_indicators:
            block.append(Paragraph("<b>Observed Indicators (model-extracted).</b>", self.body))
            for i in exp.observed_indicators:
                block.append(Paragraph(f"&bull; {sanitize_paragraph(i)}", self.body))
        if exp.potential_attack_context:
            block.append(Paragraph("<b>Potential Attack Context (candidates only).</b>", self.body))
            block.append(self._llm_technique_table(exp.potential_attack_context))
        if exp.recommended_actions:
            block.append(Paragraph("<b>Recommended Actions.</b>", self.body))
            for a in exp.recommended_actions:
                block.append(Paragraph(f"&bull; {sanitize_paragraph(a)}", self.body))
        if exp.limitations:
            block.append(Paragraph("<b>Limitations (model-stated).</b>", self.body))
            for l_ in exp.limitations:
                block.append(Paragraph(f"&bull; {sanitize_paragraph(l_)}", self.body))
        return block

    # ------------------------------------------------------------------ #
    # Tables
    # ------------------------------------------------------------------ #
    def _kv_table(self, rows: List[Tuple[str, str]], col2: float = 90 * mm) -> Table:
        data = [
            [
                Paragraph(k, ParagraphStyle("K", parent=self.cell, fontName="Helvetica-Bold")),
                Paragraph(v, self.cell),
            ]
            for k, v in rows
        ]
        t = Table(data, colWidths=[65 * mm, col2])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2F6")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def _technique_table(self, techniques: List[ReportSectionTechnique]) -> Table:
        header = [self._ch("ID"), self._ch("Technique"), self._ch("Score"), self._ch("Tactics")]
        rows = [header]
        for t in techniques:
            rows.append([
                Paragraph(sanitize_text(t.technique_id, 40), self.cell),
                Paragraph(sanitize_paragraph(t.technique_name, 120), self.cell),
                Paragraph(f"{t.score:.4f}", self.cell),
                Paragraph(sanitize_paragraph(", ".join(t.tactics), 200), self.cell),
            ])
        tbl = Table(rows, colWidths=[20 * mm, 48 * mm, 18 * mm, 62 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3B57")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tbl

    def _llm_technique_table(self, contexts) -> Table:
        header = [self._ch("ID"), self._ch("Technique"), self._ch("Confidence"), self._ch("Reason")]
        rows = [header]
        for c in contexts:
            rows.append([
                Paragraph(sanitize_text(c.technique_id, 40), self.cell),
                Paragraph(sanitize_paragraph(c.technique_name, 120), self.cell),
                Paragraph(sanitize_text(c.confidence, 20), self.cell),
                Paragraph(sanitize_paragraph(c.reason, 300), self.cell),
            ])
        tbl = Table(rows, colWidths=[18 * mm, 42 * mm, 20 * mm, 68 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3B57")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return tbl

    def _ch(self, text: str) -> Paragraph:
        return Paragraph(text, self.cell_header)

    # ------------------------------------------------------------------ #
    # Small helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _flatten_indicators(indicators: Dict[str, Any]) -> List[Tuple[str, Any]]:
        rows: List[Tuple[str, Any]] = []
        for key, value in (indicators or {}).items():
            if isinstance(value, dict):
                for sub, sub_val in value.items():
                    rows.append((f"{key}.{sub}", sub_val))
            else:
                rows.append((key, value))
        return rows

    @staticmethod
    def _fmt_value(value: Any) -> str:
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, float):
            if abs(value - int(value)) < 1e-9 and abs(value) < 1e15:
                return str(int(value))
            return f"{value:.4f}"
        return sanitize_text(value, 120)

    @staticmethod
    def _interpretation(content: ReportContent) -> str:
        if content.is_anomaly:
            return (
                f"The flow was flagged as anomalous: an isolation-forest anomaly score of "
                f"{content.anomaly_score:.6f} exceeds the operating threshold "
                f"{content.threshold:.6f} ({content.operating_point}). Severity is assessed as "
                f"{content.severity_level}."
            )
        return (
            f"The flow was not flagged as anomalous: an isolation-forest anomaly score of "
            f"{content.anomaly_score:.6f} is below the operating threshold {content.threshold:.6f} "
            f"({content.operating_point}). Severity is assessed as {content.severity_level}."
        )

    @staticmethod
    def _disclaimer_lines() -> List[str]:
        return [
            "Anomaly detection is probabilistic. A flagged flow is a candidate for review, not proof of malicious activity.",
            "MITRE ATT&CK results are contextual retrieval evidence, not confirmed detections or attribution.",
            "LLM output is explanatory only and must not be represented as verified diagnosis or confirmed attribution.",
            "Missing RAG or LLM data is reported honestly in this document and does not change the detection evidence.",
            "This report was generated automatically from the analysis pipeline and has not been human-reviewed.",
        ]


class ReportService:
    """Orchestrates PDF report generation + safe storage/retrieval."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else settings.reports_dir
        self.renderer = PdfReportRenderer()

    def generate(
        self,
        request: ReportGenerateRequest,
        packet: AnalysisEvidence,
        explanation: Optional[LLMExplanationOutput] = None,
    ) -> ReportResponse:
        report_id = uuid.uuid4().hex
        file_name = f"report_{report_id}.pdf"
        now = datetime.now(timezone.utc)

        content = ReportContent(
            app_name=request.app_name,
            report_type=request.report_type,
            report_id=report_id,
            request_id=packet.request_id,
            generated_at_display=now.strftime("%Y-%m-%d %H:%M:%S"),
            is_anomaly=packet.is_anomaly,
            anomaly_score=packet.anomaly_score,
            threshold=packet.threshold,
            experiment_id=packet.experiment_id,
            operating_point=packet.operating_point,
            model_version=packet.model_version,
            severity_level=packet.severity_level,
            risk_score=packet.risk_score,
            calibration_note=packet.calibration_note,
            indicators=summarize_flow(packet.flow_dict),
            techniques=[
                ReportSectionTechnique(
                    technique_id=r.technique_id,
                    technique_name=r.technique_name,
                    score=r.score,
                    tactics=r.tactics,
                    description=r.description,
                    mitigations=r.mitigations,
                    technique_type=r.type,
                )
                for r in packet.retrieved
            ],
            explanation=explanation,
        )

        try:
            pdf_bytes = self.renderer.render(content)
        except Exception as exc:
            logger.error(f"PDF rendering failed: {exc.__class__.__name__}: {exc}")
            raise ReportGenerationException(
                "PDF rendering failed", details={"error": exc.__class__.__name__}
            ) from exc

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / file_name
            output_path.write_bytes(pdf_bytes)
        except OSError as exc:
            logger.error(f"Could not write report file: {exc}")
            raise ReportGenerationException(
                "Could not write report file", details={"error": exc.__class__.__name__}
            ) from exc

        logger.info(
            f"Report generated: report_id={report_id} request_id={packet.request_id} "
            f"bytes={len(pdf_bytes)} output={output_path}"
        )
        return ReportResponse(
            report_id=report_id,
            request_id=packet.request_id,
            report_type=request.report_type,
            app_name=request.app_name,
            status="generated",
            file_name=file_name,
            pdf_path=f"reports/{file_name}",
            download_url=f"/api/v1/reports/{report_id}/download",
            size_bytes=len(pdf_bytes),
            generated_at=now.isoformat(),
        )

    def report_file(self, report_id: str) -> Path:
        """Resolve a generated PDF strictly inside the output directory."""
        if not _REPORT_ID_RE.fullmatch(str(report_id or "")):
            raise ReportNotFoundException("Invalid report identifier")
        base = self.output_dir.resolve()
        target = (self.output_dir / f"report_{report_id}.pdf").resolve()
        if base not in target.parents:
            raise ReportNotFoundException("Report not found")
        if not target.is_file():
            raise ReportNotFoundException("Report not found")
        return target