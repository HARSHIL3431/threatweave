from fastapi import APIRouter, Depends
from app.dependencies import get_ml_service, get_rag_service_public
from app.schemas.health import HealthResponse
from app.services.ml_service import MLService
from app.services.rag_service import RagService

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Check backend and ML model readiness")
def get_health(
    ml_service: MLService = Depends(get_ml_service),
    rag_service: RagService = Depends(get_rag_service_public),
) -> HealthResponse:
    """Return backend status, ML model readiness, and RAG index state."""
    rag_state = rag_service.status().get("status", "unavailable")
    if ml_service.is_loaded:
        return HealthResponse(
            status="healthy",
            model_status="ready",
            model_version=ml_service.model_version,
            experiment_id=ml_service.experiment_id,
            active_operating_point=ml_service.operating_point,
            active_threshold=round(ml_service.active_threshold, 6),
            rag_status=rag_state,
        )
    return HealthResponse(
        status="degraded",
        model_status="not_loaded",
        rag_status=rag_state,
    )