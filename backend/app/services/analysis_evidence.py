"""Shared evidence builder used by /explain and /reports/generate.

Both endpoints need the same pipeline output for a flow:

    ML inference -> severity -> MITRE mapping (RAG-grounded) -> RAG evidence

Single implementation so report generation never duplicates (or drifts from)
the detection/explain business logic.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.schemas.detection import NetworkFlowRequest
from app.services.mitre_service import MitreService
from app.services.rag_service import RagService, RetrievalResult
from app.services.severity_service import SeverityService

logger = get_logger("analysis_evidence")


@dataclass
class AnalysisEvidence:
    """Everything derived for one flow by the shared pipeline."""

    request_id: str
    flow_dict: Dict[str, Any]
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    experiment_id: str
    operating_point: str
    model_version: str
    severity_level: str
    risk_score: float
    calibration_note: str
    mitre_techniques: List[str] = field(default_factory=list)
    retrieved: List[RetrievalResult] = field(default_factory=list)


def build_analysis_evidence(
    ml_service,
    rag_service: RagService,
    flow_request: NetworkFlowRequest,
    top_k: int,
    request_id: str,
) -> AnalysisEvidence:
    """Run the shared pipeline for a single flow and bundle the evidence.

    RAG retrieval is best-effort and non-fatal (mirrors /detect): when the index
    is disabled or unavailable the retrieved list is simply empty, and the
    detection/severity evidence is still produced.
    """
    flow_dict = flow_request.to_feature_dict()

    ml_result = ml_service.predict(flow_dict)
    severity = SeverityService().calculate_severity(
        anomaly_score=ml_result.anomaly_score,
        threshold=ml_result.threshold,
    )
    mitre_techniques = MitreService(rag_service=rag_service).map_techniques(
        flow=flow_dict,
        anomaly_score=ml_result.anomaly_score,
        is_anomaly=ml_result.is_anomaly,
    )
    retrieved = rag_service.retrieve_evidence(flow_dict, top_k=top_k)

    return AnalysisEvidence(
        request_id=request_id,
        flow_dict=flow_dict,
        is_anomaly=ml_result.is_anomaly,
        anomaly_score=round(ml_result.anomaly_score, 6),
        threshold=round(ml_result.threshold, 6),
        experiment_id=ml_result.experiment_id,
        operating_point=ml_result.operating_point,
        model_version=ml_result.model_version,
        severity_level=severity.level,
        risk_score=severity.risk_score,
        calibration_note=severity.calibration_note,
        mitre_techniques=mitre_techniques,
        retrieved=retrieved,
    )