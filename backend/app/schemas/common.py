from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard structured error response model."""
    error_code: str = Field(..., description="Machine-readable error classification code")
    message: str = Field(..., description="Human-readable description of error")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context or validation errors")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of error"
    )
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")
