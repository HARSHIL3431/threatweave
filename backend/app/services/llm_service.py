"""LLM-based incident explanation service.

Design constraints honored by this layer:

- The ML + severity + RAG detection pipeline is fully autonomous. LLM calls are
  made ONLY through the dedicated /explain surface (Phase 10: no automatic LLM
  call on every /detect). The inherited `explain()` hook remains a no-op so the
  detection pipeline never depends on an LLM provider being reachable.
- Output is structured and strictly validated (schema + technique grounding).
- The LLM cannot invent or "confirm" ATT&CK IDs: validated entries reference
  only technique IDs that RAG supplied, and each name must match the RAG name.
- Failure is always controlled (LLM_UNAVAILABLE / PROVIDER_ERROR / TIMEOUT /
  VALIDATION_ERROR) and never corrupts a detection result.
- No API keys or secrets are ever logged. Request metadata (request_id,
  provider, model, latency, outcome, validation result) is logged instead.
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.exceptions import AppException, LLMUnavailableException
from app.core.logging import get_logger
from app.schemas.llm import LLMEvidence, LLMExplanationOutput
from app.services.llm_providers import LLMProvider, create_provider
from app.services.llm_validation import validate_llm_output

logger = get_logger("llm_service")


class LLMExplanation:
    """Legacy structure returned by the detection-flow explain hook (Phase 2)."""

    summary: Optional[str]
    reasoning: Optional[str]
    recommendations: List[str]

    def __init__(
        self,
        summary: Optional[str] = None,
        reasoning: Optional[str] = None,
        recommendations: Optional[List[str]] = None,
    ):
        self.summary = summary
        self.reasoning = reasoning
        self.recommendations = recommendations or []


class LLMService:
    """Incident explanation layer backed by a pluggable LLM provider."""

    def __init__(self, enabled: Optional[bool] = None, provider: Optional[LLMProvider] = None):
        self.enabled = settings.LLM_ENABLED if enabled is None else bool(enabled)
        self.provider = provider or create_provider()

    def explain(
        self,
        flow: Dict[str, Any],
        anomaly_score: float,
        is_anomaly: bool,
        mitre_context: Optional[List[str]] = None,
        rag_context: Optional[List[str]] = None,
    ) -> LLMExplanation:
        """Detection-flow explain hook (kept as a NON-BLOCKING no-op).

        Per Phase 10 the /detect pipeline intentionally does not make an LLM
        call on every request. The dedicated /explain endpoint is the LLM
        surface and calls generate_explanation() instead. This hook preserves
        backward compatibility and guarantees detection never depends on the
        LLM; it returns an empty explanation structure regardless of settings.
        """
        _ = (flow, anomaly_score, is_anomaly, mitre_context, rag_context)
        return LLMExplanation(summary=None, reasoning=None, recommendations=[])

    def generate_explanation(self, evidence: LLMEvidence) -> Tuple[LLMExplanationOutput, float]:
        """Generate, validate, and return a structured grounded explanation.

        Raises controlled AppExceptions (LLM_UNAVAILABLE, LLM_PROVIDER_ERROR,
        LLM_TIMEOUT, LLM_VALIDATION_ERROR) on any failure. Returns
        (explanation, latency_ms).
        """
        if not self.enabled:
            raise LLMUnavailableException(
                "LLM explanation is disabled (LLM_ENABLED=false). "
                "Detection remains fully functional."
            )

        allowed_ids = {t.technique_id: t.technique_name for t in evidence.rag_results}

        start = time.perf_counter()
        try:
            raw = self.provider.generate(evidence)
            latency_ms = (time.perf_counter() - start) * 1000.0
        except AppException:
            latency_ms = (time.perf_counter() - start) * 1000.0
            self._log(evidence, latency_ms, "failure", "rejected")
            raise
        except Exception as exc:  # belt-and-braces: never leak unexpected errors
            latency_ms = (time.perf_counter() - start) * 1000.0
            self._log(evidence, latency_ms, "failure", "rejected")
            raise LLMUnavailableException(
                f"Unexpected LLM provider failure: {exc.__class__.__name__}"
            ) from exc

        try:
            validated = validate_llm_output(raw, allowed_ids)
        except AppException:
            self._log(evidence, latency_ms, "failure", "rejected")
            raise

        self._log(
            evidence, latency_ms, "success", "passed",
            extra={"attack_techniques": [c.technique_id for c in validated.potential_attack_context]},
        )
        return validated, latency_ms

    def _log(
        self,
        evidence: LLMEvidence,
        latency_ms: float,
        outcome: str,
        validation: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        provider_name = getattr(self.provider, "name", "unknown")
        model_name = getattr(self.provider, "model", "")
        payload: Dict[str, Any] = {
            "request_id": evidence.request_id,
            "provider": provider_name,
            "model": model_name,
            "latency_ms": round(latency_ms, 2),
            "result": outcome,
            "validation": validation,
        }
        if extra:
            payload.update(extra)
        if outcome == "success":
            logger.info(f"LLM explanation generated: {payload}")
        else:
            logger.warning(f"LLM explanation failed: {payload}")