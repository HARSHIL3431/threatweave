from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Overall health status: 'healthy', 'degraded', or 'unhealthy'")
    model_status: str = Field(..., description="Model readiness: 'ready', 'not_loaded', or 'error'")
    model_version: Optional[str] = Field(default=None, description="Frozen model version identifier")
    experiment_id: Optional[str] = Field(default=None, description="Experiment identifier (e.g. 'with_port')")
    active_operating_point: Optional[str] = Field(default=None, description="Active operating point (e.g. 'OP-A')")
    active_threshold: Optional[float] = Field(default=None, description="Active decision threshold value")
    rag_status: Optional[str] = Field(default=None, description="RAG index state: 'ready' or 'unavailable'")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp"
    )
