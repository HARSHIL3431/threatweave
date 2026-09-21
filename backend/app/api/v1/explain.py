from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Header

from app.core.logging import get_logger
from app.dependencies import (
    get_llm_service,
    get_ml_service,
    get_rag_service_evidence,
)
from app.schemas.detection import AttackContext, DetectionDetails, SeverityDetails
from app.schemas.llm import (
    EvidenceTechnique,
    ExplainRequest,
    ExplainResponse,
    LLMEvidence,
    LLMMetadata,
)
from app.services.analysis_evidence import build_analysis_evidence
from app.services.llm_prompts import summarize_flow
from app.services.llm_service import LLMService
from app.services.ml_service import MLService
from app.services.rag_service import RagService, format_retrieval_result

logger = get_logger("explain_api")

router = APIRouter(tags=["LLM"])


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Generate a grounded, structured LLM explanation for a network flow",
    description=(
        "Re-runs the standard pipeline (ML -> severity -> RAG retrieval) on the supplied flow, "
        "then asks the configured LLM provider for a strictly validated, structured explanation. "
        "Retrieved ATT&CK techniques are candidates only; the LLM cannot invent or confirm "
        "technique IDs. Returns 503 LLM_UNAVAILABLE when LLM_ENABLED=false or no API key is set."
    ),
)
def explain_flow(
    request: ExplainRequest,
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
    ml_service: MLService = Depends(get_ml_service),
    rag_service: RagService = Depends(get_rag_service_evidence),
    llm_service: LLMService = Depends(get_llm_service),
) -> ExplainResponse:
    """Generate a grounded structured explanation end-to-end for one flow."""
    request_id = x_correlation_id or str(uuid.uuid4())
    packet = build_analysis_evidence(
        ml_service=ml_service,
        rag_service=rag_service,
        flow_request=request.flow,
        top_k=request.top_k,
        request_id=request_id,
    )

    evidence = LLMEvidence(
        request_id=request_id,
        is_anomaly=packet.is_anomaly,
        anomaly_score=packet.anomaly_score,
        threshold=packet.threshold,
        experiment_id=packet.experiment_id,
        operating_point=packet.operating_point,
        severity_level=packet.severity_level,
        risk_score=packet.risk_score,
        flow_summary=summarize_flow(packet.flow_dict),
        rag_results=[
            EvidenceTechnique(
                technique_id=r.technique_id,
                technique_name=r.technique_name,
                score=r.score,
                description=r.description,
                tactics=r.tactics,
                detection=r.detection,
                mitigations=r.mitigations,
            )
            for r in packet.retrieved
        ],
    )

    explanation, latency_ms = llm_service.generate_explanation(evidence)

    logger.info(
        f"Explanation completed for {request_id}: "
        f"provider={llm_service.provider.name}, latency_ms={latency_ms:.2f}"
    )

    return ExplainResponse(
        request_id=request_id,
        detection=DetectionDetails(
            is_anomaly=packet.is_anomaly,
            anomaly_score=packet.anomaly_score,
            threshold=packet.threshold,
            experiment_id=packet.experiment_id,
            operating_point=packet.operating_point,
        ),
        severity=SeverityDetails(
            level=packet.severity_level,
            risk_score=packet.risk_score,
            calibration_note=packet.calibration_note,
        ),
        attack_context=AttackContext(
            mitre_techniques=packet.mitre_techniques,
            retrieved_context=[format_retrieval_result(r) for r in packet.retrieved],
        ),
        explanation=explanation,
        llm=LLMMetadata(
            provider=llm_service.provider.name,
            model=llm_service.provider.model,
            latency_ms=round(latency_ms, 2),
            validated=True,
        ),
    )