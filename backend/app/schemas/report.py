from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.detection import NetworkFlowRequest
from app.schemas.llm import LLMExplanationOutput

#: Allowed report kinds. "analysis" is the general form; "anomaly"/"benign"
#: hint the expected outcome and slightly vary the interpretation wording.
ReportType = Literal["analysis", "anomaly", "benign"]


class ReportGenerateRequest(BaseModel):
    """Request to generate a server-side PDF report for a network-flow analysis.

    The endpoint derives the detection evidence (ML -> severity -> RAG) using
    the SAME shared pipeline /explain uses; no business logic is duplicated and
    nothing can be fabricated by the caller. An optional, already-validated LLM
    explanation may be attached; it is re-validated (grounding against the
    freshly retrieved technique IDs) before it is rendered.
    """

    report_type: ReportType = "analysis"
    app_name: str = Field(
        default="AI-Powered Cybersecurity Anomaly Detection System",
        max_length=120,
    )
    request_id: Optional[str] = Field(default=None, max_length=128)
    flow: NetworkFlowRequest
    top_k: int = Field(default=5, ge=1, le=20)
    llm_explanation: Optional[LLMExplanationOutput] = None

    model_config = ConfigDict(extra="forbid")


class ReportResponse(BaseModel):
    """Result of a successful report generation."""

    report_id: str
    request_id: str
    report_type: str
    app_name: str
    status: Literal["generated", "failed"] = "generated"
    file_name: str
    pdf_path: str
    download_url: str
    size_bytes: int
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )