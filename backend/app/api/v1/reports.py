import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header
from fastapi.responses import FileResponse

from app.core.logging import get_logger
from app.core.exceptions import InvalidInputException
from app.dependencies import (
    get_ml_service,
    get_rag_service_evidence,
    get_report_service,
)
from app.schemas.report import ReportGenerateRequest, ReportResponse
from app.services.analysis_evidence import build_analysis_evidence
from app.services.llm_validation import validate_llm_output
from app.services.ml_service import MLService
from app.services.rag_service import RagService
from app.services.report_service import ReportService

logger = get_logger("reports_api")

router = APIRouter(tags=["Reports"])


@router.post(
    "/reports/generate",
    response_model=ReportResponse,
    summary="Generate a professional PDF report for a network-flow analysis",
    description=(
        "Re-runs the shared analysis pipeline (ML -> severity -> RAG) for the supplied flow and "
        "renders a server-side PDF report with detection summary, observed indicators, retrieved "
        "MITRE ATT&CK context (candidates only) and, when provided, a validated LLM explanation. "
        "Report files are stored under the controlled reports directory; no user-supplied paths "
        "are ever used."
    ),
)
def generate_report(
    request: ReportGenerateRequest,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    ml_service: MLService = Depends(get_ml_service),
    rag_service: RagService = Depends(get_rag_service_evidence),
    report_service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    """Generate a structured PDF report from the shared analysis evidence."""
    request_id = x_correlation_id or request.request_id or str(uuid.uuid4())
    packet = build_analysis_evidence(
        ml_service=ml_service,
        rag_service=rag_service,
        flow_request=request.flow,
        top_k=request.top_k,
        request_id=request_id,
    )

    # P0-3: the caller-chosen report_type must not contradict the computed
    # outcome. "analysis" is neutral and always allowed; "anomaly"/"benign"
    # that mismatch the detection would present a failed or negative result
    # as its opposite, so they are rejected instead of rendered.
    if request.report_type == "anomaly" and not packet.is_anomaly:
        raise InvalidInputException(
            "report_type 'anomaly' does not match the computed BENIGN outcome "
            "for this flow. Use report_type 'analysis' or 'benign'."
        )
    if request.report_type == "benign" and packet.is_anomaly:
        raise InvalidInputException(
            "report_type 'benign' does not match the computed ANOMALOUS outcome "
            "for this flow. Use report_type 'analysis' or 'anomaly'."
        )

    # LLM explanation is optional input. If supplied it MUST pass the same
    # strict grounding validation used by /explain (ids subset of RAG results,
    # correct names, valid confidence enum, remediation grounding) before it
    # may appear in a report.
    explanation = None
    if request.llm_explanation is not None:
        allowed_ids = {t.technique_id: t.technique_name for t in packet.retrieved}
        allowed_mitigations = {
            mitigation
            for technique in packet.retrieved
            for mitigation in technique.mitigations
        }
        explanation = validate_llm_output(
            request.llm_explanation.model_dump_json(), allowed_ids,
            allowed_mitigations,
        )

    report = report_service.generate(request, packet, explanation)
    logger.info(
        f"Report generation completed: request_id={request_id} "
        f"report_id={report.report_id} llm_included={explanation is not None}"
    )
    return report


@router.get(
    "/reports/{report_id}/download",
    summary="Download a generated PDF report by id",
    description="Returns the generated PDF. The report id is a server-issued 32-hex UUID.",
)
def download_report(
    report_id: str,
    report_service: ReportService = Depends(get_report_service),
) -> FileResponse:
    """Stream a generated report from the controlled storage directory."""
    path = report_service.report_file(report_id)
    return FileResponse(path, media_type="application/pdf", filename=path.name)