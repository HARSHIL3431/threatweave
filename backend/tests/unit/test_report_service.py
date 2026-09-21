"""Unit tests for the report/PDF generation layer.

PDFs are rendered fully offline with reportlab and inspected via pypdf.
"""
import io
import re

import pytest
from pypdf import PdfReader

from app.core.exceptions import ReportGenerationException, ReportNotFoundException
from app.schemas.llm import LLMExplanationOutput, PotentialAttackContext
from app.services.analysis_evidence import AnalysisEvidence
from app.services.report_service import (
    PdfReportRenderer,
    ReportContent,
    ReportService,
    sanitize_paragraph,
    sanitize_text,
)


def _content(**overrides) -> ReportContent:
    defaults = dict(
        app_name="AI-Powered Cybersecurity Anomaly Detection System",
        report_type="analysis",
        report_id="a" * 32,
        request_id="req-unit-report",
        generated_at_display="2026-09-20 12:00:00",
        is_anomaly=True,
        anomaly_score=0.540229,
        threshold=0.521919,
        experiment_id="with_port",
        operating_point="OP-A",
        model_version="isolation_forest_v1",
        severity_level="medium",
        risk_score=0.7,
        calibration_note="c",
        indicators={"destination_port": 12345, "flag_counts": {"ack": 5}, "suspicious_zero_duration": True},
        techniques=[],
        explanation=None,
    )
    defaults.update(overrides)
    return ReportContent(**defaults)


def _pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "".join(page.extract_text() or "" for page in reader.pages)


# --------------------------------------------------------------------------- #
# Sanitization
# --------------------------------------------------------------------------- #
def test_sanitize_text_strips_control_chars_and_non_ascii():
    assert sanitize_text("a\x00b\x07c\nd") == "abc\nd"
    assert sanitize_text("caf\u00e9 \u2014 \u4e2d\u6587 ok") == "café - ?? ok"
    assert sanitize_text(None) == ""


def test_sanitize_paragraph_escapes_markup():
    assert sanitize_paragraph("<b>x</b> & y") == "&lt;b&gt;x&lt;/b&gt; &amp; y"


def test_sanitize_truncation():
    assert len(sanitize_text("x" * 5000, max_len=100)) == 100


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def test_render_produces_valid_pdf_bytes():
    pdf = PdfReportRenderer().render(_content())
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


def test_render_includes_expected_sections():
    content = _content(techniques=[
        _technique("T1046", "Network Service Discovery", 0.5, ["discovery"], "Scan open ports.", ["M-FIRST"])
    ])
    text = _pdf_text(PdfReportRenderer().render(content))
    assert "Network Anomaly Analysis Report" in text
    assert "Report Metadata" in text
    assert "Detection Summary" in text
    assert "ANOMALOUS" in text
    assert "Observed Network Indicators" in text
    assert "MITRE ATT&CK" in text and "retrieved-not-confirmed" in text
    assert "T1046" in text and "Network Service Discovery" in text
    assert "Limitations" in text
    assert "retrieval evidence" in text


def test_render_benign_status_wording():
    content = _content(is_anomaly=False, anomaly_score=0.45, severity_level="low")
    text = _pdf_text(PdfReportRenderer().render(content))
    assert "BENIGN" in text
    assert "not flagged as anomalous" in text


def test_render_omits_llm_section_when_no_explanation():
    text = _pdf_text(PdfReportRenderer().render(_content(explanation=None)))
    assert "No LLM explanation was available" in text
    assert "Potential Attack Context (candidates only)" not in text


def test_render_includes_llm_section_when_explanation_present():
    exp = _explanation()
    text = _pdf_text(PdfReportRenderer().render(_content(explanation=exp)))
    assert "Anomalous flow observed." in text
    assert "Potential Attack Context (candidates only)" in text
    assert "T1046" in text
    assert "Recommended Actions." in text


def test_render_shows_no_rag_context_honestly():
    text = _pdf_text(PdfReportRenderer().render(_content(techniques=[])))
    assert "No MITRE ATT" in text and "no relevant candidates" in text


def test_render_does_not_crash_on_markup_injection():
    evil = _technique("T1046", "Network Service Discovery", 0.5, [],
                      "<script>alert('xss')</script>\n<b>bold</b> junk", ["M-FIRST"])
    pdf = PdfReportRenderer().render(_content(techniques=[evil], app_name="<b>App</b> <i>Name</i>"))
    assert pdf[:5] == b"%PDF-"


# --------------------------------------------------------------------------- #
# Secret hygiene
# --------------------------------------------------------------------------- #
def test_render_never_includes_environment_api_key(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-test-secret-12345")
    text = _pdf_text(PdfReportRenderer().render(_content()))
    assert "sk-test-secret-12345" not in text


def test_report_service_never_writes_environment_secrets(monkeypatch, tmp_path):
    from app.core.config import settings

    planetary_key = "AKIA-DEMO-SECRET-9999"
    monkeypatch.setattr(settings, "LLM_API_KEY", "sk-other-secret")
    monkeypatch.setattr(settings, "MODEL_PATH", f"../etc/{planetary_key}")  # hypothetical env value
    svc = ReportService(output_dir=tmp_path)
    resp = svc.generate(_make_request(), _make_packet(), explanation=None)
    pdf = (tmp_path / resp.file_name).read_bytes()
    assert planetary_key not in _pdf_text(pdf)


# --------------------------------------------------------------------------- #
# ReportService storage / safety
# --------------------------------------------------------------------------- #
def test_report_service_writes_pdf_and_schema(tmp_path):
    svc = ReportService(output_dir=tmp_path)
    resp = svc.generate(_make_request(), _make_packet(), explanation=None)

    assert re.fullmatch(r"[0-9a-f]{32}", resp.report_id)
    assert resp.status == "generated"
    assert resp.file_name == f"report_{resp.report_id}.pdf"
    assert resp.download_url == f"/api/v1/reports/{resp.report_id}/download"
    assert resp.pdf_path == f"reports/{resp.file_name}"
    assert resp.request_id == "req-report-1"
    assert resp.report_type == "analysis"

    path = tmp_path / resp.file_name
    assert path.is_file()
    assert path.read_bytes()[:5] == b"%PDF-"
    assert resp.size_bytes == path.stat().st_size


def test_report_file_validation_blocks_traversal(tmp_path):
    svc = ReportService(output_dir=tmp_path)
    for bad in ("..", "../../../etc/passwd", "..%2f..%2fetc%2fpasswd", "abc", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA1"):
        with pytest.raises(ReportNotFoundException):
            svc.report_file(bad)


def test_report_file_missing_report_not_found(tmp_path):
    svc = ReportService(output_dir=tmp_path)
    with pytest.raises(ReportNotFoundException):
        svc.report_file("0" * 32)


def test_report_file_resolves_existing_file(tmp_path):
    svc = ReportService(output_dir=tmp_path)
    resp = svc.generate(_make_request(), _make_packet(), explanation=None)
    resolved = svc.report_file(resp.report_id)
    assert resolved.is_file()
    assert str(resolved.parent).startswith(str(tmp_path.resolve()))


def test_report_generation_fails_safely_when_output_dir_is_a_file(tmp_path):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("I am a file")
    svc = ReportService(output_dir=blocker)
    with pytest.raises(ReportGenerationException):
        svc.generate(_make_request(), _make_packet(), explanation=None)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _technique(tid, name, score, tactics, desc, mitigations):
    from app.services.report_service import ReportSectionTechnique

    return ReportSectionTechnique(
        technique_id=tid, technique_name=name, score=score,
        tactics=tactics, description=desc, mitigations=mitigations,
    )


def _explanation() -> LLMExplanationOutput:
    return LLMExplanationOutput(
        summary="Anomalous flow observed.",
        anomaly_assessment="Score exceeds threshold.",
        observed_indicators=["Elevated packet rate"],
        potential_attack_context=[
            PotentialAttackContext(
                technique_id="T1046", technique_name="Network Service Discovery",
                confidence="medium", reason="Candidate matching flow.",
            )
        ],
        recommended_actions=["Investigate."],
        limitations=["Not confirmed."],
    )


def _make_request():
    from app.schemas.report import ReportGenerateRequest

    return ReportGenerateRequest(
        report_type="analysis",
        request_id="req-report-1",
        flow=_flow(),
        top_k=5,
        llm_explanation=None,
    )


def _flow():
    from app.schemas.detection import NetworkFlowRequest

    raw = {
        "Destination Port": 443, "Flow Duration": 100000, "Total Fwd Packets": 12,
        "Total Backward Packets": 5, "Total Length of Fwd Packets": 500,
        "Total Length of Bwd Packets": 200, "Fwd Packet Length Max": 100,
        "Fwd Packet Length Min": 20, "Fwd Packet Length Mean": 41.6,
        "Fwd Packet Length Std": 20.0, "Bwd Packet Length Max": 60,
        "Bwd Packet Length Min": 10, "Bwd Packet Length Mean": 40.0,
        "Bwd Packet Length Std": 10.0, "Flow Bytes/s": 7000.0,
        "Flow Packets/s": 170.0, "Flow IAT Mean": 1000.0, "Flow IAT Std": 100.0,
        "Flow IAT Max": 3000.0, "Flow IAT Min": 200.0, "Fwd IAT Total": 5000.0,
        "Fwd IAT Mean": 900.0, "Fwd IAT Std": 90.0, "Fwd IAT Max": 2900.0,
        "Fwd IAT Min": 190.0, "Bwd IAT Total": 4000.0, "Bwd IAT Mean": 800.0,
        "Bwd IAT Std": 80.0, "Bwd IAT Max": 2800.0, "Bwd IAT Min": 180.0,
        "Fwd PSH Flags": 0, "Fwd URG Flags": 0, "Fwd Header Length": 240.0,
        "Fwd Packets/s": 120.0, "Bwd Packets/s": 50.0, "Min Packet Length": 10.0,
        "Max Packet Length": 100.0, "Packet Length Mean": 45.0, "Packet Length Std": 15.0,
        "Packet Length Variance": 225.0, "FIN Flag Count": 0, "RST Flag Count": 0,
        "PSH Flag Count": 0, "ACK Flag Count": 5, "URG Flag Count": 0,
        "Down/Up Ratio": 0.4, "Average Packet Size": 45.0,
        "Init_Win_bytes_forward": 29200, "Init_Win_bytes_backward": 29200,
        "act_data_pkt_fwd": 8, "min_seg_size_forward": 20, "Active Mean": 0.0,
        "Active Std": 0.0, "Active Max": 0.0, "Active Min": 0.0,
        "Idle Mean": 0.0, "Idle Std": 0.0, "Idle Max": 0.0, "Idle Min": 0.0,
        "Is_Zero_Duration": 0,
    }
    return NetworkFlowRequest(**raw)


def _make_packet() -> AnalysisEvidence:
    return AnalysisEvidence(
        request_id="req-report-1",
        flow_dict={"Destination Port": 443, "Flow Duration": 100000, "Flow Packets/s": 170.0,
                   "Is_Zero_Duration": 0, "ACK Flag Count": 5},
        is_anomaly=True,
        anomaly_score=0.540229,
        threshold=0.521919,
        experiment_id="with_port",
        operating_point="OP-A",
        model_version="isolation_forest_v1",
        severity_level="medium",
        risk_score=0.7,
        calibration_note="c",
        mitre_techniques=["T1046"],
        retrieved=[],
    )