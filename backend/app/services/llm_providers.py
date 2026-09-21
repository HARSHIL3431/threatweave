"""LLM provider abstraction.

The application is not coupled to a single vendor: providers implement a
minimal `generate(evidence) -> raw JSON string` contract. Default is an
OpenAI-compatible chat-completions provider (works with any compatible API by
changing LLM_OPENAI_BASE_URL). A deterministic offline "mock" provider exists
for local/CI use without any API key or cost; it is fully grounded in the
supplied evidence and never fabricates technique IDs.

No API keys are hard-coded. Runtime errors surface as controlled AppExceptions:
- missing/empty API key         -> LLMUnavailableException (503 LLM_UNAVAILABLE)
- provider HTTP/transport error -> LLMProviderErrorException (502)
- provider timeout              -> LLMTimeoutException (504)
"""
import json
import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from app.core.config import settings
from app.core.exceptions import (
    LLMProviderErrorException,
    LLMTimeoutException,
    LLMUnavailableException,
)
from app.core.logging import get_logger
from app.schemas.llm import EvidenceTechnique, LLMEvidence
from app.services.llm_prompts import build_chat_messages

logger = get_logger("llm_providers")


class LLMProvider(ABC):
    """Minimal provider interface for LLM-based explanation generation."""

    name: str = "base"
    model: str = ""

    @abstractmethod
    def generate(self, evidence: LLMEvidence) -> str:
        """Return raw model output (a JSON-only string) for the evidence."""


class OpenAIProvider(LLMProvider):
    """OpenAI-compatible chat completions provider (httpx, no SDK dependency)."""

    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key if api_key not in (None, "") else settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.timeout = timeout if timeout is not None else settings.LLM_TIMEOUT
        base = (base_url or settings.LLM_OPENAI_BASE_URL).rstrip("/")
        self.endpoint = f"{base}/chat/completions"

    def generate(self, evidence: LLMEvidence) -> str:
        if not self.api_key:
            raise LLMUnavailableException(
                "LLM provider requires an API key. Set LLM_API_KEY (or configure "
                "LLM_PROVIDER=mock for offline use). No API key is configured, so "
                "LLM explanation is unavailable."
            )

        messages = build_chat_messages(evidence)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.endpoint, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutException(
                f"LLM provider call timed out after {self.timeout}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderErrorException(
                f"LLM provider transport error: {exc.__class__.__name__}"
            ) from exc

        if response.status_code != 200:
            body = ""
            try:
                body = response.json().get("error", {}).get("message", "") or response.text[:300]
            except Exception:
                body = response.text[:300]
            raise LLMProviderErrorException(
                f"LLM provider returned HTTP {response.status_code}: {body}"
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderErrorException(
                "LLM provider returned an unexpected response shape"
            ) from exc

        if not content or not str(content).strip():
            raise LLMProviderErrorException("LLM provider returned an empty response")

        return str(content)


class MockProvider(LLMProvider):
    """Deterministic offline provider.

    Produces a schema-valid, fully grounded JSON explanation derived ONLY from
    the supplied evidence (ML detection + severity + flow summary + retrieved
    ATT&CK candidates). It never invents technique IDs: potential_attack_context
    is populated exclusively from evidence.rag_results, and is [] when RAG
    supplied no context. Used for local/CI run and as a development stub.
    """

    name = "mock"
    model = "mock-grounded-local"

    def generate(self, evidence: LLMEvidence) -> str:
        indicators = _describe_indicators(evidence)
        context = _derive_technique_candidates(evidence.rag_results)
        actions = _derive_actions(evidence.rag_results)

        limitations = [
            "Generated by the local offline mock provider; no live LLM model was queried.",
        ]
        if evidence.rag_results:
            limitations.append(
                "Retrieved ATT&CK techniques are candidates only and are not confirmed attacks."
            )
        else:
            limitations.append(
                "No ATT&CK context was retrieved, so no potential attack techniques are asserted."
            )

        explanation = {
            "summary": (
                f"The network flow was flagged as {'anomalous' if evidence.is_anomaly else 'benign'} "
                f"with anomaly score {evidence.anomaly_score:.4f} against threshold "
                f"{evidence.threshold:.4f}, assessed as {evidence.severity_level} severity."
            ),
            "anomaly_assessment": (
                f"Anomaly score {evidence.anomaly_score:.4f} "
                f"({'exceeds' if evidence.is_anomaly else 'is below'}) the operating threshold "
                f"{evidence.threshold:.4f} (experiment {evidence.experiment_id}, {evidence.operating_point})."
            ),
            "observed_indicators": indicators,
            "potential_attack_context": context,
            "recommended_actions": actions,
            "limitations": limitations,
        }
        return json.dumps(explanation, ensure_ascii=False, indent=2)


def _describe_indicators(evidence: LLMEvidence) -> List[str]:
    indicators: List[str] = []
    if evidence.flow_summary.get("suspicious_zero_duration"):
        indicators.append("Flow has a suspicious zero-duration connection profile.")
    else:
        port = evidence.flow_summary.get("destination_port")
        if port:
            indicators.append(f"Network flow targeting destination port {port}.")
        bps = evidence.flow_summary.get("flow_bytes_per_s")
        if bps is not None:
            indicators.append(f"Observed flow rate of {bps} bytes/s.")
    if evidence.severity_level in ("high", "critical"):
        indicators.append(f"Severity assessed as {evidence.severity_level}.")
    return indicators


def _derive_technique_candidates(results: List[EvidenceTechnique]) -> List[dict]:
    candidates = []
    for r in results:
        score = float(r.score)
        confidence = "high" if score >= 0.55 else ("medium" if score >= 0.45 else "low")
        tactics = ", ".join(r.tactics) if r.tactics else "unknown tactic"
        candidates.append(
            {
                "technique_id": r.technique_id,
                "technique_name": r.technique_name,
                "confidence": confidence,
                "reason": (
                    f"Retrieved candidate {r.technique_id} ({r.technique_name}, "
                    f"{tactics}) matched the flow characteristics with score {score:.4f}; "
                    "candidate only, not confirmed."
                ),
            }
        )
    return candidates


def _derive_actions(results: List[EvidenceTechnique]) -> List[str]:
    actions: List[str] = []
    seen: set[str] = set()
    for r in results:
        for m in r.mitigations:
            m = m.strip()
            if m and m.lower() not in seen:
                seen.add(m.lower())
                actions.append(f"Mitigation (per {r.technique_id}): {m}")
    if not actions:
        actions.append("Review the flagged flow and corroborate indicators before acting.")
    return actions[:5]


def create_provider(name: Optional[str] = None) -> LLMProvider:
    """Instantiate the configured provider. Never raises (controlled behavior)."""
    provider_name = (name or settings.llm_provider_slug()).strip().lower()
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "mock":
        return MockProvider()
    return _UnknownProvider(provider_name)


class _UnknownProvider(LLMProvider):
    """Placeholder for an unrecognized provider; fails controlled on use."""

    name = "unknown"

    def __init__(self, provider_name: str):
        self._configured_name = provider_name
        self.model = provider_name

    def generate(self, evidence: LLMEvidence) -> str:
        raise LLMUnavailableException(
            f"Unknown LLM provider '{self._configured_name}'. Configured providers: "
            "'openai' (OpenAI-compatible) or 'mock' (offline)."
        )