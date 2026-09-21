from time import perf_counter

from fastapi import APIRouter, Depends

from app.dependencies import get_rag_service_public
from app.schemas.rag import (
    RagQueryRequest,
    RagQueryResponse,
    RagSearchResult,
    RagStatusResponse,
)
from app.services.rag_service import RagService

router = APIRouter(tags=["RAG"])


@router.get(
    "/rag/status",
    response_model=RagStatusResponse,
    summary="RAG knowledge base status",
    description="Indicates whether the MITRE ATT&CK RAG index is loaded and searchable.",
)
def get_rag_status(
    rag: RagService = Depends(get_rag_service_public),
) -> RagStatusResponse:
    """Return RAG index readiness without rebuilding anything."""
    return RagStatusResponse(**rag.status())


@router.post(
    "/rag/query",
    response_model=RagQueryResponse,
    summary="Query the MITRE ATT&CK RAG knowledge base",
    description=(
        "Retrieve grounded MITRE ATT&CK techniques relevant to a natural-language query. "
        "Returns 503 RAG_UNAVAILABLE when the index has not been built "
        "(run scripts/build_mitre_index.py)."
    ),
)
def rag_query(
    payload: RagQueryRequest,
    rag: RagService = Depends(get_rag_service_public),
) -> RagQueryResponse:
    """Retrieve potentially relevant ATT&CK techniques for the query."""
    start = perf_counter()
    results = rag.query(payload.query, top_k=payload.top_k)
    elapsed_ms = (perf_counter() - start) * 1000.0

    return RagQueryResponse(
        query=payload.query,
        top_k=payload.top_k,
        result_count=len(results),
        retrieval_time_ms=round(elapsed_ms, 3),
        results=[
            RagSearchResult(
                technique_id=r.technique_id,
                technique_name=r.technique_name,
                score=r.score,
                description=r.description,
                tactics=r.tactics,
                detection=r.detection,
                mitigations=r.mitigations,
                technique_type=r.type,
            )
            for r in results
        ],
    )