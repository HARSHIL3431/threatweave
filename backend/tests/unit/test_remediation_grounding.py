"""P1-9 tests: remediation-advice grounding and safety.

Deterministic and offline (canned providers only). No network, no real LLM,
no secrets. Asserts validator behavior, endpoint error categories, privacy
of error details, and fixture-driven failure modes from
remediation_grounding_cases_v1.json (synthetic, unvalidated labels).
"""
import json
from pathlib import Path

import pytest

from app.core.exceptions import LLMValidationErrorException
from app.schemas.llm import EvidenceTechnique, LLMEvidence
from app.services.llm_providers import MockProvider
from app.services.llm_service import LLMService
from app.services.llm_validation import validate_llm_output

_ALLOWED = {"T1046": "Network Service Discovery"}
_MITIGATIONS = ["Monitor network traffic for unusual activity", "Disable unused services"]


class FakeProvider:
    def __init__(self, raw):
        self.raw = raw
        self.name = "fake"
        self.model = "fake-model"

    def generate(self, evidence):
        return self.raw


def _evidence(**overrides):
    params = dict(
        request_id="req-p19-1",
        is_anomaly=True,
        anomaly_score=0.54,
        threshold=0.52,
        experiment_id="with_port",
        operating_point="OP-A",
        severity_level="medium",
        risk_score=0.7,
        flow_summary={"destination_port": 80},
        rag_results=[
            EvidenceTechnique(
                technique_id="T1046", technique_name="Network Service Discovery",
                score=0.5, description="d", tactics=["discovery"],
                detection=None, mitigations=list(_MITIGATIONS),
            )
        ],
    )
    params.update(overrides)
    return LLMEvidence(**params)


def _output(**overrides):
    data = {
        "summary": "Anomalous flow observed.",
        "anomaly_assessment": "Score exceeds threshold.",
        "observed_indicators": ["Elevated packet rate"],
        "potential_attack_context": [],
        "recommended_actions": ["Investigate the flow."],
        "limitations": ["Not confirmed."],
    }
    data.update(overrides)
    return json.dumps(data)


# Fixture-driven failure modes (14 required shapes + mitigation exemption).
def test_remediation_fixture_cases():
    fixture = json.loads(
        (Path(__file__).parent.parent / "fixtures" / "remediation_grounding_cases_v1.json")
        .read_text(encoding="utf-8")
    )
    assert fixture["version"] == "remediation-grounding-cases-v1"
    assert len(fixture["cases"]) == 15
    allowed = fixture["allowed_ids"]
    mitigations = fixture["allowed_mitigations"]
    for case in fixture["cases"]:
        raw = json.dumps(case["output"])
        if case["expect"] == "valid":
            assert validate_llm_output(raw, allowed, mitigations) is not None, case["name"]
        elif case["expect"] == "valid-with-gap":
            # Passes validation AND documents a known detection boundary.
            assert validate_llm_output(raw, allowed, mitigations) is not None, case["name"]
            assert case.get("gap"), case["name"]
        else:
            assert case["expect"] == "invalid", case["name"]
            with pytest.raises(LLMValidationErrorException) as exc:
                validate_llm_output(raw, allowed, mitigations)
            assert case["error_key"] in exc.value.details, case["name"]


# Mitigation-grounded actions pass even with high-impact verbs.
def test_mitigation_grounding_exemptions():
    grounded = _output(recommended_actions=[
        "Mitigation (per T1046): Disable unused services.",
        "Monitor network traffic for unusual activity on the flagged host.",
    ])
    assert validate_llm_output(grounded, _ALLOWED, _MITIGATIONS) is not None


def test_template_with_unallowed_id_is_not_grounded():
    action = _output(recommended_actions=["Mitigation (per T9999): Disable everything now."])
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(action, _ALLOWED, _MITIGATIONS)
    assert "unqualified_high_impact_action" in exc.value.details
    assert "ungrounded_technique_mentions" in exc.value.details


# Qualification variants.
@pytest.mark.parametrize("action", [
    "Consider disabling the affected account.",
    "Isolate the host after verifying scope with the on-call analyst.",
    "Block the suspicious address once corroborated by firewall logs.",
    "Quarantine may be appropriate pending review.",
])
def test_qualified_high_impact_passes(action):
    assert validate_llm_output(_output(recommended_actions=[action]),
                               _ALLOWED, _MITIGATIONS) is not None


@pytest.mark.parametrize("action", [
    "ISOLATE the host now.",
    "Wipe the workstation and reimage it.",
    "Revoke every credential in the directory.",
    "Terminate the database service immediately.",
    "Shut down the core switch.",
])
def test_unqualified_high_impact_fails(action):
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(_output(recommended_actions=[action]),
                            _ALLOWED, _MITIGATIONS)
    entry = exc.value.details["unqualified_high_impact_action"][0]
    assert entry["index"] == 0
    assert entry["trigger"]


# CVE facts are never supported by pipeline evidence.
def test_specific_cve_rejected():
    out = _output(summary="Exploits CVE-2024-1234 against the mail server.")
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(out, _ALLOWED, _MITIGATIONS)
    assert exc.value.details["unsupported_factual_claim"][0]["claim"] == "CVE-2024-1234"


def test_cve_database_mention_without_id_passes():
    out = _output(recommended_actions=["Check vendor advisories for known issues."])
    assert validate_llm_output(out, _ALLOWED, _MITIGATIONS) is not None


# Endpoint behavior: unqualified remediation fails closed; mock still passes.
def test_endpoint_rejects_unqualified_remediation(loaded_ml_service, sample_flows):
    from fastapi.testclient import TestClient

    from app.dependencies import get_llm_service, get_ml_service, get_rag_service_evidence
    from app.main import app
    from app.services.rag_service import RagService

    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    app.dependency_overrides[get_rag_service_evidence] = lambda: RagService(enabled=False)
    app.dependency_overrides[get_llm_service] = lambda: LLMService(
        enabled=True, provider=FakeProvider(_output(
            recommended_actions=["Disable all user accounts now."])))
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json()["error_code"] == "LLM_VALIDATION_ERROR"
    assert "unqualified_high_impact_action" in response.json()["details"]


def test_mock_with_trigger_word_mitigation_stays_valid():
    evidence = _evidence()
    evidence.rag_results[0].mitigations = ["Disable or Remove Feature or Program"]
    raw = MockProvider().generate(evidence)
    allowed = {"T1046": "Network Service Discovery"}
    out = validate_llm_output(raw, allowed, ["Disable or Remove Feature or Program"])
    assert any("T1046" in a for a in out.recommended_actions)


# Privacy: error details carry short excerpts only, never prompts or secrets.
def test_error_details_contain_no_sensitive_material():
    from app.services import observability as obs

    obs.reset()
    service = LLMService(enabled=True, provider=FakeProvider(_output(
        recommended_actions=["Disable all user accounts now."])))
    with pytest.raises(LLMValidationErrorException) as exc:
        service.generate_explanation(_evidence())
    blob = json.dumps(exc.value.details)
    assert "Bearer" not in blob and "sk-" not in blob
    assert "destination_port" not in blob
    for entry in exc.value.details["unqualified_high_impact_action"]:
        assert len(entry["trigger"]) <= 40
    snap = obs.get_snapshot()
    assert "unqualified_high_impact_action" in str(
        snap["events"].get("llm.validation.rejected", {}))
    obs.reset()


# Observability category for the new rejection keys.
def test_new_rejection_keys_are_bounded_categories():
    from app.services import observability as obs

    obs.reset()
    service = LLMService(enabled=True, provider=FakeProvider(_output(
        recommended_actions=["Wipe every workstation tonight."])))
    with pytest.raises(LLMValidationErrorException):
        service.generate_explanation(_evidence())
    cats = obs.get_snapshot()["events"]["llm.validation.rejected"]
    assert set(cats) == {"unqualified_high_impact_action"}
    obs.reset()
