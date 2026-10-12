"""P1-3 tests: explanation grounding, uncertainty, and safe degradation.

All LLM calls are faked (canned providers, httpx MockTransport). No network,
no real provider, no secrets. Tests assert observable outputs and error
categories, not prose.
"""
import json
from pathlib import Path

import httpx
import pytest

from app.core.exceptions import (
    LLMProviderErrorException,
    LLMValidationErrorException,
)
from app.schemas.llm import EvidenceTechnique, LLMEvidence
from app.services.llm_providers import MockProvider, OpenAIProvider
from app.services.llm_prompts import build_user_content, format_provenance_note
from app.services.llm_service import LLMService
from app.services.llm_validation import validate_llm_output


class FakeProvider:
    def __init__(self, raw):
        self.raw = raw
        self.name = "fake"
        self.model = "fake-model"
        self.calls = 0

    def generate(self, evidence):
        self.calls += 1
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw


def _evidence(rag_ids=(("T1046", "Network Service Discovery"),), **overrides):
    params = dict(
        request_id="req-p13-1",
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
                technique_id=tid, technique_name=name, score=0.5,
                description="d", tactics=["discovery"], detection=None,
                mitigations=[],
            )
            for tid, name in rag_ids
        ],
    )
    params.update(overrides)
    return LLMEvidence(**params)


def _valid_output(**overrides):
    data = {
        "summary": "Anomalous flow observed.",
        "anomaly_assessment": "Score exceeds threshold.",
        "observed_indicators": ["Elevated packet rate"],
        "potential_attack_context": [
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
    data.update(overrides)
    return json.dumps(data)


_ALLOWED = {"T1046": "Network Service Discovery"}


# 1. Valid grounded explanation end to end (fake provider, real validation).
def test_grounded_candidate_passes_end_to_end():
    service = LLMService(enabled=True, provider=FakeProvider(_valid_output()))
    out, _ = service.generate_explanation(_evidence())
    assert out.potential_attack_context[0].technique_id == "T1046"
    assert "candidate" in out.potential_attack_context[0].reason.lower()


# 2/14. Fabricated IDs rejected everywhere, including smuggled prose mentions.
def test_smuggled_id_in_summary_rejected():
    out = _valid_output(summary="Possibly linked to T9999 infrastructure.")
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(out, _ALLOWED)
    assert any(
        m["technique_id"] == "T9999"
        for m in exc.value.details["ungrounded_technique_mentions"]
    )


def test_smuggled_id_in_recommendations_rejected():
    out = _valid_output(recommended_actions=["Block all T9999 traffic immediately."])
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(out, _ALLOWED)
    assert exc.value.details["ungrounded_technique_mentions"]


def test_allowed_ids_may_be_mentioned_in_prose():
    out = _valid_output(
        summary="T1046 remains only a candidate, not a finding.",
        recommended_actions=["Review guidance for T1046."],
    )
    validated = validate_llm_output(out, _ALLOWED)
    assert validated.summary.startswith("T1046")


# 3. Correct ID with wrong name still rejected.
def test_name_mismatch_rejected():
    data = json.loads(_valid_output())
    data["potential_attack_context"][0]["technique_name"] = "Port Scan Plus"
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), _ALLOWED)
    assert exc.value.details["technique_name_mismatch"]


# 4. Retrieved technique framed as confirmed attack is rejected.
def test_confirmatory_reason_rejected():
    data = json.loads(_valid_output())
    data["potential_attack_context"][0]["reason"] = (
        "T1046 is confirmed as the attack used here."
    )
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(json.dumps(data), _ALLOWED)
    assert exc.value.details["confirmatory_language"]


def test_confirmatory_summary_rejected():
    out = _valid_output(summary="This flow is definitely malicious.")
    with pytest.raises(LLMValidationErrorException) as exc:
        validate_llm_output(out, _ALLOWED)
    assert exc.value.details["confirmatory_language"]


def test_hedged_and_negated_language_passes():
    out = _valid_output(
        summary="A possible attack that is not confirmed.",
        anomaly_assessment="The score suggests review but proves nothing.",
    )
    validated = validate_llm_output(out, _ALLOWED)
    assert validated.summary.startswith("A possible attack")


def test_mock_reason_candidate_framing_passes():
    raw = MockProvider().generate(_evidence())
    validated = validate_llm_output(raw, _ALLOWED)
    assert "candidate only" in validated.potential_attack_context[0].reason


# 5/6/9. No retrieved techniques: empty context accepted, limitation ensured.
def test_empty_rag_gets_limitation_ensured():
    service = LLMService(enabled=True, provider=FakeProvider(_valid_output(
        potential_attack_context=[], limitations=["Review needed."]
    )))
    out, _ = service.generate_explanation(_evidence(rag_ids=[]))
    assert out.potential_attack_context == []
    assert any("no mitre att&ck context was retrieved" in l.lower() for l in out.limitations)


def test_empty_rag_existing_attck_limitation_not_duplicated():
    service = LLMService(enabled=True, provider=FakeProvider(_valid_output(
        potential_attack_context=[], limitations=["No ATT&CK context was retrieved."]
    )))
    out, _ = service.generate_explanation(_evidence(rag_ids=[]))
    assert sum("att&ck" in l.lower() for l in out.limitations) == 1


def test_missing_optional_evidence_still_validates():
    service = LLMService(enabled=True, provider=FakeProvider(_valid_output(
        potential_attack_context=[]
    )))
    out, _ = service.generate_explanation(_evidence(rag_ids=[], flow_summary={}))
    assert out.summary


# 7. Retrieval integrity failure degrades to empty context, explanation stands.
def test_integrity_failure_degrades_safely(
    loaded_ml_service, sample_flows, tmp_path, fake_embedder
):
    from fastapi.testclient import TestClient

    from app.dependencies import get_llm_service, get_ml_service, get_rag_service_evidence
    from app.main import app
    from app.services.rag_service import RagService, clear_rag_cache

    corrupt_dir = tmp_path / "corrupt"
    corrupt_dir.mkdir()
    (corrupt_dir / "index.faiss").write_bytes(b"not a faiss index" * 64)
    (corrupt_dir / "metadata.json").write_text("{}", encoding="utf-8")
    app.dependency_overrides[get_ml_service] = lambda: loaded_ml_service
    app.dependency_overrides[get_rag_service_evidence] = lambda: RagService(
        enabled=True,
        index_path=corrupt_dir / "index.faiss",
        metadata_path=corrupt_dir / "metadata.json",
        embedder=fake_embedder,
    )
    app.dependency_overrides[get_llm_service] = lambda: LLMService(
        enabled=True, provider=FakeProvider(_valid_output(potential_attack_context=[]))
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/explain",
                json={"flow": sample_flows["anomalous_flow"]["input"], "top_k": 5},
            )
    finally:
        app.dependency_overrides.clear()
        clear_rag_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["attack_context"]["retrieved_context"] == []
    assert data["attack_context"]["mitre_techniques"] == []
    assert data["detection"]["is_anomaly"] is True  # ML evidence intact
    assert any(
        "no mitre att&ck context was retrieved" in l.lower()
        for l in data["explanation"]["limitations"]
    )


# 8. Unknown/stale provenance surfaced honestly in prompt and note.
def test_provenance_note_variants():
    assert "unavailable" in format_provenance_note({"status": "unavailable"})
    unknown = format_provenance_note({"status": "ready", "built_at": None})
    assert "unknown" in unknown
    stale = format_provenance_note({
        "status": "ready", "built_at": "2025-01-01T00:00:00+00:00",
        "knowledge_age_days": 300, "is_stale": True,
    })
    assert "stale" in stale and "not the ATT&CK release date" in stale
    fresh = format_provenance_note({
        "status": "ready", "built_at": "2026-10-01T00:00:00+00:00",
        "knowledge_age_days": 10, "is_stale": False,
    })
    assert "stale" not in fresh and "2026-10-01" in fresh


def test_provenance_note_reaches_prompt():
    content = build_user_content(_evidence(rag_provenance_note="MITRE knowledge base unavailable."))
    assert "MITRE knowledge base unavailable." in content
    assert "potential_attack_context" in content  # schema section intact


def test_empty_provenance_note_adds_nothing():
    content = build_user_content(_evidence())
    assert "Knowledge note" not in content


# 10/11. Malformed and empty outputs fail as validation errors, not crashes.
def test_empty_string_output_rejected():
    with pytest.raises(LLMValidationErrorException):
        validate_llm_output("   ", _ALLOWED)


def test_none_output_rejected():
    service = LLMService(enabled=True, provider=FakeProvider(None))
    with pytest.raises(LLMValidationErrorException):
        service.generate_explanation(_evidence())


def test_non_object_json_rejected():
    with pytest.raises(LLMValidationErrorException):
        validate_llm_output("[1, 2, 3]", _ALLOWED)


# 12. Provider failures stay controlled (incl. rate limiting); no secrets leak.
def test_rate_limit_maps_to_controlled_provider_error(monkeypatch):
    real_client = httpx.Client

    def factory(*args, **kwargs):
        return real_client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(
                    429, json={"error": {"message": "rate limited"}}
                )
            ),
            timeout=kwargs.get("timeout"),
        )

    monkeypatch.setattr(httpx, "Client", factory)
    from app.services.llm_providers import OpenAIProvider

    service = LLMService(
        enabled=True, provider=OpenAIProvider(api_key="test-key", timeout=5.0)
    )
    with pytest.raises(LLMProviderErrorException) as exc:
        service.generate_explanation(_evidence())
    assert "429" in str(exc.value)
    assert "test-key" not in str(exc.value)


# 13. Invalid structured fields rejected; unexpected fields ignored safely.
def test_unexpected_fields_ignored():
    data = json.loads(_valid_output())
    data["brand_new_field"] = {"nested": [1, 2, 3]}
    data["potential_attack_context"][0]["extra"] = "dropped"
    validated = validate_llm_output(json.dumps(data), _ALLOWED)
    assert validated.summary == "Anomalous flow observed."
    assert not hasattr(validated.potential_attack_context[0], "extra")


def test_invalid_confidence_rejected():
    data = json.loads(_valid_output())
    data["potential_attack_context"][0]["confidence"] = "certain"
    with pytest.raises(LLMValidationErrorException):
        validate_llm_output(json.dumps(data), _ALLOWED)


# 15. Deterministic validation outcomes on repeated inputs.
def test_repeated_validation_identical():
    raw = _valid_output()
    first = validate_llm_output(raw, _ALLOWED)
    second = validate_llm_output(raw, _ALLOWED)
    assert first == second
    service = LLMService(enabled=True, provider=FakeProvider(raw))
    out_a, _ = service.generate_explanation(_evidence())
    out_b, _ = service.generate_explanation(_evidence())
    assert out_a == out_b


# F. Fixture-driven grounding cases (synthetic, honestly labeled).
def test_grounding_fixture_cases():
    fixture = json.loads(
        (Path(__file__).parent.parent / "fixtures" / "llm_grounding_cases_v1.json")
        .read_text(encoding="utf-8")
    )
    assert fixture["version"] == "llm-grounding-cases-v1"
    assert len(fixture["cases"]) == 7
    for case in fixture["cases"]:
        allowed = case.get("allowed", fixture["allowed"])
        raw = json.dumps(case["output"])
        if case["expect"] == "valid":
            assert validate_llm_output(raw, allowed) is not None, case["name"]
        else:
            with pytest.raises(LLMValidationErrorException) as exc:
                validate_llm_output(raw, allowed)
            assert case["error_key"] in exc.value.details, case["name"]
