from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.detection import NetworkFlowRequest, DetectionDetails, SeverityDetails, AttackContext


class EvidenceTechnique(BaseModel):
    """A RAG-retrieved technique handed to the LLM as grounded (unconfirmed) context."""

    technique_id: str
    technique_name: str
    score: float
    description: str = ""
    tactics: List[str] = Field(default_factory=list)
    detection: Any = None
    mitigations: List[str] = Field(default_factory=list)


class LLMEvidence(BaseModel):
    """Structured, trusted evidence passed to the LLM explanation layer.

    The LLM must base its answer ONLY on this evidence plus the retrieved
    context. Retrieved techniques are candidates, never confirmed detections.
    """

    request_id: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    experiment_id: str
    operating_point: str
    severity_level: str
    risk_score: float
    flow_summary: Dict[str, Any] = Field(default_factory=dict)
    rag_results: List[EvidenceTechnique] = Field(default_factory=list)


class PotentialAttackContext(BaseModel):
    """A single candidate ATT&CK technique referenced by the LLM explanation.

    technique_id MUST be one of the ids supplied by RAG; the LLM is never
    allowed to invent new ATT&CK ids.
    """

    technique_id: str
    technique_name: str
    confidence: str = Field(..., description="One of: low, medium, high")
    reason: str


class LLMExplanationOutput(BaseModel):
    """Validated structured output from the LLM explanation layer."""

    summary: str
    anomaly_assessment: str
    observed_indicators: List[str] = Field(default_factory=list)
    potential_attack_context: List[PotentialAttackContext] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class LLMMetadata(BaseModel):
    provider: str
    model: str
    latency_ms: float
    validated: bool = True


class ExplainRequest(BaseModel):
    """Standalone explanation request.

    The endpoint re-runs the standard pipeline (ML -> severity -> RAG) on the
    supplied flow so the explanation is grounded in the same evidence /detect
    would compute. No persistence layer / request store exists yet, so the
    evidence is passed directly rather than via a detection request id.
    """

    flow: NetworkFlowRequest
    top_k: int = Field(default=5, ge=1, le=20)

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class ExplainResponse(BaseModel):
    request_id: str
    detection: DetectionDetails
    severity: SeverityDetails
    attack_context: AttackContext
    explanation: LLMExplanationOutput
    llm: LLMMetadata