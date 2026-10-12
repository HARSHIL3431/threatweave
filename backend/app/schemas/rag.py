from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RagQueryRequest(BaseModel):
    """Query the MITRE ATT&CK RAG knowledge base."""
    query: str = Field(..., min_length=1, max_length=2000, description="Natural-language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of techniques to return")

    @field_validator("query")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query must not be empty or whitespace")
        return v


class RagSearchResult(BaseModel):
    """A single grounded MITRE ATT&CK technique retrieval hit."""
    technique_id: str
    technique_name: str
    score: float = Field(..., description="Cosine similarity (normalized embeddings)")
    description: str = ""
    tactics: List[str] = Field(default_factory=list)
    detection: Optional[str] = None
    mitigations: List[str] = Field(default_factory=list)
    technique_type: str = "technique"  # "technique" | "sub-technique"


class RagQueryResponse(BaseModel):
    """Structured response from the RAG query endpoint."""
    query: str
    top_k: int
    result_count: int
    retrieval_time_ms: float
    results: List[RagSearchResult] = Field(default_factory=list)


class RagStatusResponse(BaseModel):
    """State of the RAG knowledge base for health/operation checks."""
    status: str = Field(..., description="'ready' when the index is loaded, otherwise 'unavailable'")
    index_path: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_dim: Optional[int] = None
    doc_count: Optional[int] = None
    technique_count: Optional[int] = None
    subtechnique_count: Optional[int] = None
    detail: Optional[str] = None
    # P0-1 provenance (all optional: older artifacts lack them).
    # built_at is the index *build* time, never the ATT&CK release time.
    source_url: Optional[str] = None
    bundle_sha256: Optional[str] = None
    bundle_bytes: Optional[int] = None
    attack_pattern_count: Optional[int] = None
    attack_version: Optional[str] = None
    max_modified: Optional[str] = None
    built_at: Optional[str] = None
    knowledge_age_days: Optional[int] = None
    knowledge_age_status: Optional[str] = Field(
        default=None, description="'fresh', 'stale', or 'unknown'"
    )
    is_stale: bool = False
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp",
    )