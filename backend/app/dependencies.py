from typing import Optional
from fastapi import Depends
from app.core.config import settings
from app.services.detection_service import DetectionService
from app.services.ml_service import MLService
from app.services.severity_service import SeverityService
from app.services.mitre_service import MitreService
from app.services.rag_service import RagService
from app.services.llm_service import LLMService

# Global MLService instance initialized once during lifespan
_ml_service_instance: Optional[MLService] = None


def set_global_ml_service(instance: MLService) -> None:
    """Store global MLService initialized in lifespan."""
    global _ml_service_instance
    _ml_service_instance = instance


def get_ml_service() -> MLService:
    """Dependency provider for MLService."""
    if _ml_service_instance is None:
        # Fallback if accessed before lifespan or in standalone tests
        svc = MLService()
        return svc
    return _ml_service_instance


def get_rag_service() -> RagService:
    """Dependency provider for RAG within the detection flow.

    RAG here is gated by the RAG_ENABLED setting. The index is lazy-loaded and
    cached, so ML detection remains functional if RAG is missing or disabled.
    """
    return RagService(enabled=settings.RAG_ENABLED)


def get_rag_service_public() -> RagService:
    """Dependency provider for the standalone RAG query/status endpoints.

    The standalone RAG API works whenever a built index exists; the
    RAG_ENABLED flag only controls automatic retrieval inside detection.
    """
    return RagService(enabled=True)


def get_llm_service() -> LLMService:
    """Dependency provider for the standalone LLM explanation endpoint.

    Honors LLM_ENABLED; constructing the service never raises (unknown
    providers fail controlled at call time). Detection never depends on it.
    """
    return LLMService()


def get_rag_service_evidence() -> RagService:
    """RAG service for /explain: retrieval is attempted when enabled and is
    non-fatal, so the explanation layer stays grounded on detection alone even
    if the index is not available."""
    return RagService(enabled=settings.RAG_ENABLED)


def get_report_service():
    """Dependency provider for the report generation service.

    Writes PDFs into the controlled settings.reports_dir directory. Tests may
    override this to point at a temporary directory.
    """
    from app.services.report_service import ReportService

    return ReportService()


def get_detection_service(
    ml_service: MLService = Depends(get_ml_service),
) -> DetectionService:
    """Dependency provider for DetectionService."""
    rag_service = RagService(enabled=settings.RAG_ENABLED)
    return DetectionService(
        ml_service=ml_service,
        severity_service=SeverityService(),
        mitre_service=MitreService(rag_service=rag_service),
        rag_service=rag_service,
        llm_service=LLMService(),
    )