"""Unit tests for the LLM explanation layer.

These tests never call a real LLM API: a canned FakeProvider returns raw
strings, letting us exercise every validation and failure path with zero cost.
"""
import json

import pytest

from app.core.exceptions import (
    LLMProviderErrorException,
    LLMTimeoutException,
    LLMUnavailableException,
    LLMValidationErrorException,
)
from app.schemas.llm import EvidenceTechnique, LLMEvidence
from app.services.llm_providers import MockProvider, OpenAIProvider, create_provider
from app.services.llm_service import LLMService, LLMExplanation
from app.services.llm_validation import validate_llm_output


class FakeProvider:
    def __init__(self, raw: str):
        self.raw = raw
        self.name = "fake"
        self.model = "fake-model"
        self.calls = 0

    def generate(self, evidence):
        self.calls += 1
        return self.raw


class RaisingProvider:
    def __init__(self, error: Exception):
        self.error = error
        self.name = "raising"
        self.model = "fake-model"

    def generate(self, evidence):
        raise self.error


def _evidence(rag_ids=None):
    if rag_ids is None:
        rag_ids = [("T1046", "Network Service Discovery")]
    rag = [
        EvidenceTechnique(
            technique_id=tid,
            technique_name=name,
            score=0.5,
            description="Some grounded description",
            tactics=["discovery"],
            detection="Watch for repeated connections",
            mitigations=["M-FIRST"],
        )
        for tid, name in rag_ids
    ]
    return LLMEvidence(
        request_id="req-unit-1",
        is_anomaly=True,
        anomaly_score=0.54,
        threshold=0.52,
        experiment_id="with_port",
        operating_point="OP-A",
        severity_level="medium",
        risk_score=0.7,
        flow_summary={"destination_port": 80, "flow_packets_per_s": 10.0},
        rag_results=rag,
    )


def _valid_json(attack_context=None):
    return json.dumps(
        {
            "summary": "Anomalous flow observed.",
            "anomaly_assessment": "Score exceeds threshold.",
            "observed_indicators": ["Elevated packet rate"],
            "potential_attack_context": attack_context
            or [
                {
                    "technique_id": "T1046",
                    "technique_name": "Network Service Discovery",
                    "confidence": "medium",
                    "reason": "Candidate matching flow characteristics.",
                }
            ],
            "recommended_actions": ["Investigate the flow."],
            "limitations": ["Not confirmed."],
        }
    )


def _fenced_json():
    return "```json\n" + _valid_json() + "\n```"


# --------------------------------------------------------------------------- #
# validate_llm_output - schema / grounding checks
# --------------------------------------------------------------------------- #
def test_validate_accepts_valid_output_with_grounded_techniques():
    allowed = {"T1046": "Network Service Discovery"}
    out = validate_llm_output(_valid_json(), allowed)
    assert out.summary == "Anomalous flow observed."
    assert out.anomaly_assessment.startswith("Score exceeds")
    assert out.observed_indicators == ["Elevated packet rate"]
    assert len(out.potential_attack_context) == 1
    ctx = out.potential_attack_context[0]
    assert ctx.technique_id == "T1046"
    assert ctx.technique_name == "Network Service Discovery"
    assert ctx.confidence == "medium"
    assert ctx.reason


def test_validate_accepts_markdown_fenced_output():
    out = validate_llm_output(_fenced_json(), {"T1046": "Network Service Discovery"})
    assert out.potential_attack_context[0].technique_id == "T1046"
    assert out.summary == "Anomalous flow observed."


def test_validate_rejects_malformed_json():
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output("not json at all", {"T1046": "Network Service Discovery"})
    assert exc.value.error_code == "LLM_VALIDATION_ERROR"
    assert exc.value.details["field"] == "root"


def test_validate_rejects_missing_required_field():
    data = json.loads(_valid_json())
    del data["summary"]
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), {"T1046": "Network Service Discovery"})
    assert "summary" in exc.value.details["missing_fields"]


def test_validate_rejects_fabricated_technique_id_t9999():
    allowed = {"T1046": "Network Service Discovery", "T1016.001": "System Network Configuration Discovery", "T1049": "System Network Connections Discovery"}
    data = json.loads(_valid_json())
    data["potential_attack_context"] = [{"technique_id": "T9999", "technique_name": "Not Real", "confidence": "high", "reason": "made up"}]
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), allowed)
    offenders = exc.value.details["ungrounded_techniques"]
    assert any(o.get("technique_id") == "T9999" for o in offenders)


def test_validate_rejects_technique_name_mismatch():
    data = json.loads(_valid_json())
    data["potential_attack_context"][0]["technique_name"] = "Renamed Technique"
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), {"T1046": "Network Service Discovery"})
    assert exc.value.details["technique_name_mismatch"][0]["technique_id"] == "T1046"
    assert exc.value.details["technique_name_mismatch"][0]["expected_name"] == "Network Service Discovery"


def test_validate_rejects_invalid_confidence():
    data = json.loads(_valid_json())
    data["potential_attack_context"][0]["confidence"] = "certain"
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), {"T1046": "Network Service Discovery"})
    assert exc.value.details["invalid_confidence"][0]["confidence"] == "certain"


def test_validate_rejects_empty_explanation_strings():
    data = json.loads(_valid_json())
    data["summary"] = "   "
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), {"T1046": "Network Service Discovery"})
    assert "summary" in exc.value.details["empty_strings"]


def test_validate_rejects_attack_context_when_no_rag_context():
    data = json.loads(_valid_json())
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), {})
    assert exc.value.details["ungrounded_techniques"]


def test_validate_accepts_empty_attack_context_when_no_rag_context():
    data = json.loads(_valid_json())
    data["potential_attack_context"] = []
    out = validate_llm_output(json.dumps(data), {})
    assert out.potential_attack_context == []


# --------------------------------------------------------------------------- #
# LLMService.generate_explanation - end-to-end with fake provider
# --------------------------------------------------------------------------- #
def test_generate_explanation_returns_validated_output():
    service = LLMService(enabled=True, provider=FakeProvider(_valid_json()))
    out, latency = service.generate_explanation(_evidence())
    assert out.summary == "Anomalous flow observed."
    assert out.potential_attack_context[0].technique_id == "T1046"
    assert latency >= 0.0


def test_generate_explanation_when_llm_disabled():
    service = LLMService(enabled=False, provider=FakeProvider(_valid_json()))
    with pytest.raises(LLMUnavailableException) as exc:
        service.generate_explanation(_evidence())
    assert exc.value.error_code == "LLM_UNAVAILABLE"


def test_generate_explanation_missing_api_key():
    provider = OpenAIProvider(api_key="")
    assert provider.api_key == ""
    service = LLMService(enabled=True, provider=provider)
    with pytest.raises(LLMUnavailableException) as exc:
        service.generate_explanation(_evidence())
    assert exc.value.error_code == "LLM_UNAVAILABLE"


def test_generate_explanation_provider_error():
    service = LLMService(
        enabled=True,
        provider=RaisingProvider(LLMProviderErrorException("provider exploded")),
    )
    with pytest.raises(LLMProviderErrorException):
        service.generate_explanation(_evidence())


def test_generate_explanation_provider_timeout():
    service = LLMService(
        enabled=True,
        provider=RaisingProvider(LLMTimeoutException("too slow")),
    )
    with pytest.raises(LLMTimeoutException):
        service.generate_explanation(_evidence())


def test_generate_explanation_rejects_fabricated_t9999():
    data = json.loads(_valid_json())
    data["potential_attack_context"] = [{"technique_id": "T9999", "technique_name": "Fake", "confidence": "high", "reason": "hallucinated"}]
    service = LLMService(enabled=True, provider=FakeProvider(json.dumps(data)))
    with pytest.raises(LLMValidationErrorException) as exc:
        service.generate_explanation(_evidence(rag_ids=[("T1046", "Network Service Discovery")]))
    assert any(o.get("technique_id") == "T9999" for o in exc.value.details["ungrounded_techniques"])


def test_generate_explanation_unknown_provider_is_controlled():
    service = LLMService(enabled=True, provider=create_provider("not-a-real-provider"))
    with pytest.raises(LLMUnavailableException):
        service.generate_explanation(_evidence())


# --------------------------------------------------------------------------- #
# MockProvider - offline, grounded, deterministic
# --------------------------------------------------------------------------- #
def test_mock_provider_returns_grounded_and_schema_valid():
    provider = MockProvider()
    raw = provider.generate(_evidence())
    out = validate_llm_output(raw, {"T1046": "Network Service Discovery"})
    assert out.summary
    assert out.potential_attack_context[0].technique_id == "T1046"
    assert out.potential_attack_context[0].confidence in ("low", "medium", "high")
    assert any("mock" in l.lower() for l in out.limitations)


def test_mock_provider_no_rag_context_gives_empty_attack_context():
    provider = MockProvider()
    raw = provider.generate(_evidence(rag_ids=[]))
    out = validate_llm_output(raw, {})
    assert out.potential_attack_context == []
    assert any("No ATT&CK context" in l for l in out.limitations)


def test_mock_provider_factory_and_service_integration():
    service = LLMService(enabled=True, provider=create_provider("mock"))
    out, _ = service.generate_explanation(_evidence())
    assert out.potential_attack_context[0].technique_id == "T1046"


# --------------------------------------------------------------------------- #
# Backward-compat explain hook (detection flow) stays a no-op
# --------------------------------------------------------------------------- #
def test_explain_hook_never_calls_provider_even_when_enabled():
    provider = FakeProvider(_valid_json())
    service = LLMService(enabled=True, provider=provider)
    exp = service.explain({}, 0.8, True)
    assert isinstance(exp, LLMExplanation)
    assert exp.summary is None
    assert exp.recommendations == []
    assert provider.calls == 0