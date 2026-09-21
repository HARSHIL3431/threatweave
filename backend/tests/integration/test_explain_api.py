"""Integration tests for POST /api/v1/explain and LLM/detection coexistence.

All tests are hermetic: the LLM is replaced by a canned fake provider and no
external API or API key is ever used.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_detection_service,
    get_llm_service,
    get_ml_service,
    get_rag_service_evidence,
)
from app.main import app
from app.schemas.llm import EvidenceTechnique, LLMEvidence
from app.services.detection_service import DetectionService
from app.services.llm_service import LLMService
from app.services.rag_service import RagService


class FakeProvider:
    def __init__(self, raw: str):
        self.raw = raw
        self.name = "fake"
        self.model = "fake-model"

    def generate(self, evidence: LLMEvidence) -> str:
        return self.raw


class RaisingProvider:
    def __init__(self, error: Exception):
        self.error = error
        self.name = "raising"
        self.model = "fake-model"

    def generate(self, evidence: LLMEvidence) -> str:
        raise self.error


_VALID_RESPONSE = json.dumps(
    {
        "summary": "Anomalous flow targeting port 80.",
        "anomaly_assessment": "Score 0.54 exceeds threshold 0.52.",
        "observed_indicators": ["Elevated packet rate"],
        "potential_attack_context": [],
        "recommended_actions": ["Investigate."],
        "limitations": ["None detected."],
    }
)


def _rag_disabled():
    return RagService(enabled=False, embedder=None)


def _llm_with(raw: str) -> LLMService:
    return LLMService(enabled=True, provider=FakeProvider(raw))


def _override(loader_deps: dict, *, rag=None, llm=None):
    app.dependency_overrides[get_ml_service] = lambda: loader_deps["ml"]
    app.dependency_overrides[get_rag_service_evidence] = lambda: rag or _rag_disabled()
    app.dependency_overrides[get_llm_service] = lambda: llm or _llm_with(_VALID_RESPONSE)


def test_openapi_exposes_explain_route(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/explain" in paths
    assert "post" in paths["/api/v1/explain"]


def test_explain_returns_validated_structured_output(loaded_ml_service, sample_flows):
    try:
        _override({"ml": loaded_ml_service})
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
                headers={"X-Correlation-ID": "explain-req-1"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "explain-req-1"
    assert data["detection"]["is_anomaly"] is True
    assert data["severity"]["level"] in ("medium", "high", "critical")
    exp = data["explanation"]
    assert exp["summary"] == "Anomalous flow targeting port 80."
    assert exp["potential_attack_context"] == []
    assert data["llm"]["provider"] == "fake"
    assert data["llm"]["model"] == "fake-model"
    assert data["llm"]["validated"] is True
    assert data["llm"]["latency_ms"] >= 0.0


def test_explain_barred_when_llm_disabled(loaded_ml_service, sample_flows):
    try:
        _override({"ml": loaded_ml_service}, llm=LLMService(enabled=False))
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    data = response.json()
    assert data["error_code"] == "LLM_UNAVAILABLE"


def test_explain_llm_validation_error_returns_502(loaded_ml_service, sample_flows):
    bad = json.loads(_VALID_RESPONSE)
    bad["summary"] = "   "
    try:
        _override({"ml": loaded_ml_service}, llm=_llm_with(json.dumps(bad)))
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["error_code"] == "LLM_VALIDATION_ERROR"


def test_explain_fabricated_technique_rejected(loaded_ml_service, sample_flows):
    bad = json.loads(_VALID_RESPONSE)
    bad["potential_attack_context"] = [{"technique_id": "T9999", "technique_name": "Fake", "confidence": "high", "reason": "hallucinated"}]
    try:
        _override({"ml": loaded_ml_service}, llm=_llm_with(json.dumps(bad)))
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    data = response.json()
    assert data["error_code"] == "LLM_VALIDATION_ERROR"
    ungrounded = data["details"].get("ungrounded_techniques", [])
    assert ungrounded


def test_explain_provider_error_returns_502(loaded_ml_service, sample_flows):
    from app.core.exceptions import LLMProviderErrorException

    raising = LLMService(
        enabled=True, provider=RaisingProvider(LLMProviderErrorException("upstream down"))
    )
    try:
        _override({"ml": loaded_ml_service}, llm=raising)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["error_code"] == "LLM_PROVIDER_ERROR"


def test_explain_timeout_returns_504(loaded_ml_service, sample_flows):
    from app.core.exceptions import LLMTimeoutException

    timeouter = LLMService(
        enabled=True, provider=RaisingProvider(LLMTimeoutException("slow"))
    )
    try:
        _override({"ml": loaded_ml_service}, llm=timeouter)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 504
    assert response.json()["error_code"] == "LLM_TIMEOUT"


def test_explain_invalid_request_payload_422(loaded_ml_service, sample_flows):
    try:
        _override({"ml": loaded_ml_service})
        with TestClient(app) as client:
            response = client.post("/api/v1/explain", json={"flow": {}, "top_k": 5})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_explain_supports_mock_provider_offline(loaded_ml_service, sample_flows):
    from app.services.llm_providers import MockProvider

    try:
        _override({"ml": loaded_ml_service}, llm=LLMService(enabled=True, provider=MockProvider()))
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    exp = data["explanation"]
    assert data["llm"]["provider"] == "mock"
    ids = [c["technique_id"] for c in exp["potential_attack_context"]]
    returned = [r.split(" ")[1] for r in data["attack_context"]["retrieved_context"]]
    assert set(ids).issubset(set(returned))
    assert data["llm"]["validated"] is True


def test_detection_unaffected_when_llm_fails(loaded_ml_service, sample_flows):
    """ML detection must keep working even when the LLM provider explodes."""
    from app.core.exceptions import LLMProviderErrorException

    failing_llm = LLMService(
        enabled=True, provider=RaisingProvider(LLMProviderErrorException("boom"))
    )
    svc = DetectionService(
        ml_service=loaded_ml_service,
        llm_service=failing_llm,
        rag_service=_rag_disabled(),
    )
    app.dependency_overrides[get_detection_service] = lambda: svc
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/detect",
                json=sample_flows["anomalous_flow"]["input"],
                headers={"X-Correlation-ID": "llm-fail-detect"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "llm-fail-detect"
    assert data["detection"]["is_anomaly"] is True
    assert data["severity"]["level"] in ("medium", "high", "critical")