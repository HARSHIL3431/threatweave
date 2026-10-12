"""P1-4 tests: operational observability for RAG/LLM degradation.

Deterministic and offline (FakeEmbedder stores, canned providers). Tests
assert observable counter state and safe behavior, never exact timestamps
or prose. Counters are reset around every test.
"""
import json

import pytest

from app.core.exceptions import (
    LLMProviderErrorException,
    LLMTimeoutException,
    LLMUnavailableException,
)
from app.schemas.llm import EvidenceTechnique, LLMEvidence
from app.services import observability as obs
from app.services.llm_service import LLMService
from app.services.rag_service import RagService, clear_rag_cache


@pytest.fixture(autouse=True)
def _clean_counters():
    obs.reset()
    clear_rag_cache()
    yield
    obs.reset()
    clear_rag_cache()


class FakeProvider:
    def __init__(self, raw=""):
        self.raw = raw
        self.name = "fake"
        self.model = "fake-model"

    def generate(self, evidence):
        if isinstance(self.raw, Exception):
            raise self.raw
        return self.raw


def _evidence(rag=True):
    return LLMEvidence(
        request_id="req-obs-1",
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
                detection=None, mitigations=[],
            )
        ] if rag else [],
    )


_VALID = json.dumps({
    "summary": "Anomalous flow observed.",
    "anomaly_assessment": "Score exceeds threshold.",
    "observed_indicators": ["Elevated packet rate"],
    "potential_attack_context": [],
    "recommended_actions": ["Investigate."],
    "limitations": ["Review needed."],
})


def _docs():
    return [
        {
            "text": "Technique: Port Scanning (T-TEST-1) discovery scan ports",
            "meta": {
                "technique_id": "T-TEST-1", "technique_name": "Port Scanning",
                "type": "technique", "tactics": ["discovery"],
                "description": "Scan open ports on a host",
                "detection": None, "mitigations": [],
                "data_sources": [], "platforms": [],
            },
        },
    ]


def _rag(make_store, fake_embedder, **overrides):
    index_path, metadata_path = make_store(_docs())
    params = dict(enabled=True, index_path=index_path,
                  metadata_path=metadata_path, embedder=fake_embedder, top_k=5)
    params.update(overrides)
    return RagService(**params)


# 1. Successful RAG retrieval records attempt + completion.
def test_successful_retrieval_events(make_store, fake_embedder):
    rag = _rag(make_store, fake_embedder)
    hits = rag.query("scanning open ports")
    assert len(hits) == 1
    snap = obs.get_snapshot()
    assert snap["events"][obs.RAG_QUERY_ATTEMPTED] == {obs.CATEGORY_OK: 1}
    assert snap["events"][obs.RAG_QUERY_COMPLETED] == {obs.CATEGORY_OK: 1}
    assert obs.RAG_QUERY_FAILED not in snap["events"]
    assert snap["mean_latency_ms"]["rag.query"] >= 0.0


# 2. Empty retrieval is recorded explicitly.
def test_empty_retrieval_event(tmp_path, fake_embedder):
    import faiss

    d = tmp_path / "empty"
    d.mkdir()
    index_path, metadata_path = d / "index.faiss", d / "metadata.json"
    faiss.write_index(faiss.IndexFlatIP(8), str(index_path))
    metadata_path.write_text(json.dumps({
        "embedding_model": "fake-model", "dimension": 8, "doc_count": 0,
        "technique_count": 0, "subtechnique_count": 0,
        "created_at": "2026-10-11T00:00:00+00:00", "documents": [],
    }), encoding="utf-8")
    rag = RagService(enabled=True, index_path=index_path,
                     metadata_path=metadata_path, embedder=fake_embedder)
    assert rag.query("anything", top_k=3) == []
    snap = obs.get_snapshot()
    assert snap["events"][obs.RAG_RETRIEVAL_EMPTY] == {obs.CATEGORY_OK: 1}
    assert snap["events"][obs.RAG_QUERY_COMPLETED] == {obs.CATEGORY_OK: 1}


# 3. Integrity failure is recorded and never reports ready.
def test_integrity_failure_event(tmp_path, fake_embedder):
    from app.core.exceptions import RagUnavailableException

    d = tmp_path / "corrupt"
    d.mkdir()
    index_path, metadata_path = d / "index.faiss", d / "metadata.json"
    index_path.write_bytes(b"not-a-faiss-index" * 64)
    metadata_path.write_text(json.dumps({
        "embedding_model": "x", "dimension": 8, "doc_count": 0,
        "technique_count": 0, "subtechnique_count": 0, "documents": [],
    }), encoding="utf-8")
    rag = RagService(enabled=True, index_path=index_path,
                     metadata_path=metadata_path, embedder=fake_embedder)
    assert rag.status()["status"] == "unavailable"
    with pytest.raises(RagUnavailableException):
        rag.query("anything", top_k=1)
    snap = obs.get_snapshot()
    # One observation per load attempt (status + query each tried to load).
    assert snap["events"][obs.RAG_INTEGRITY_FAILED] == {obs.CATEGORY_INTEGRITY: 2}
    assert snap["events"][obs.RAG_QUERY_FAILED][obs.CATEGORY_UNAVAILABLE] == 1


# 4. Unknown and stale provenance observations.
def test_provenance_unknown_event(make_store, fake_embedder):
    rag = _rag(make_store, fake_embedder)  # legacy: no provenance block
    status = rag.status()
    assert status["knowledge_age_status"] == "unknown"
    assert obs.get_snapshot()["events"][obs.RAG_PROVENANCE_UNKNOWN] == {obs.CATEGORY_OK: 1}


def test_provenance_stale_event(make_store, fake_embedder):
    from app.services.vector_store import VectorStore

    index_path, metadata_path = make_store(_docs())
    store = VectorStore.load(index_path, metadata_path)
    store.provenance = {"built_at": "2020-01-01T00:00:00+00:00"}
    store.save()
    clear_rag_cache()
    rag = RagService(enabled=True, index_path=index_path,
                     metadata_path=metadata_path, embedder=fake_embedder)
    assert rag.status()["is_stale"] is True
    assert obs.get_snapshot()["events"][obs.RAG_PROVENANCE_STALE] == {obs.CATEGORY_OK: 1}


# 5/6. LLM success, timeout, and provider error categories.
def test_llm_success_event():
    service = LLMService(enabled=True, provider=FakeProvider(_VALID))
    out, _ = service.generate_explanation(_evidence(rag=False))
    assert out.summary
    snap = obs.get_snapshot()
    assert snap["events"][obs.LLM_GENERATE_COMPLETED] == {obs.CATEGORY_OK: 1}
    assert snap["mean_latency_ms"]["llm.generate"] >= 0.0


def test_llm_timeout_and_provider_error_events():
    for error, category in (
        (LLMTimeoutException("slow"), obs.CATEGORY_TIMEOUT),
        (LLMProviderErrorException("down"), obs.CATEGORY_PROVIDER_ERROR),
    ):
        obs.reset()
        service = LLMService(enabled=True, provider=FakeProvider(error))
        with pytest.raises(type(error)):
            service.generate_explanation(_evidence())
        snap = obs.get_snapshot()
        assert snap["events"][obs.LLM_GENERATE_FAILED] == {category: 1}
        assert obs.LLM_GENERATE_COMPLETED not in snap["events"]


def test_llm_disabled_event():
    service = LLMService(enabled=False, provider=FakeProvider(_VALID))
    with pytest.raises(LLMUnavailableException):
        service.generate_explanation(_evidence())
    assert obs.get_snapshot()["events"][obs.LLM_GENERATE_FAILED] == {
        obs.CATEGORY_UNAVAILABLE: 1
    }


# 7. Grounding-validation rejection carries the validator's error key.
def test_validation_rejection_event():
    bad = json.loads(_VALID)
    bad["potential_attack_context"] = [{
        "technique_id": "T9999", "technique_name": "Fake",
        "confidence": "high", "reason": "hallucinated",
    }]
    service = LLMService(enabled=True, provider=FakeProvider(json.dumps(bad)))
    with pytest.raises(Exception):
        service.generate_explanation(_evidence())
    snap = obs.get_snapshot()
    assert snap["events"][obs.LLM_VALIDATION_REJECTED] == {"ungrounded_techniques": 1}
    assert snap["events"][obs.LLM_GENERATE_FAILED] == {obs.CATEGORY_VALIDATION: 1}


# 8. Degraded explanation (no ATT&CK context) is recorded.
def test_degraded_explanation_event():
    service = LLMService(enabled=True, provider=FakeProvider(_VALID))
    service.generate_explanation(_evidence(rag=False))
    assert obs.get_snapshot()["events"][obs.LLM_EXPLANATION_DEGRADED] == {
        obs.CATEGORY_DEGRADED: 1
    }


def test_grounded_explanation_not_degraded():
    service = LLMService(enabled=True, provider=FakeProvider(_VALID))
    service.generate_explanation(_evidence(rag=True))
    assert obs.LLM_EXPLANATION_DEGRADED not in obs.get_snapshot()["events"]


# 9. Safe fields only: no secrets, query text, or payloads in the snapshot.
def test_snapshot_contains_no_sensitive_data(make_store, fake_embedder):
    rag = _rag(make_store, fake_embedder)
    rag.query("super secret internal query about CVE-2099-0001")
    LLMService(enabled=True, provider=FakeProvider(_VALID)).generate_explanation(
        _evidence())
    snap = obs.get_snapshot()
    blob = json.dumps(snap)
    assert "super secret internal query" not in blob
    assert "CVE-2099-0001" not in blob
    assert "LLM_API_KEY" not in blob
    for name in snap["events"]:
        assert name.startswith(("rag.", "llm."))


# 10. Instrumentation failure never breaks requests (logging backend down).
def test_broken_counters_do_not_break_rag(make_store, fake_embedder, monkeypatch):
    import app.services.observability as obs_module

    class _DeadLogger:
        def info(self, *args, **kwargs):
            raise RuntimeError("logging backend down")

        warning = info
        error = info

    monkeypatch.setattr(obs_module, "logger", _DeadLogger())
    rag = _rag(make_store, fake_embedder)
    assert len(rag.query("scanning open ports")) == 1
    assert rag.status()["status"] == "ready"


def test_broken_counters_do_not_break_llm(monkeypatch):
    import app.services.observability as obs_module

    class _DeadLogger:
        def info(self, *args, **kwargs):
            raise RuntimeError("logging backend down")

        warning = info
        error = info

    monkeypatch.setattr(obs_module, "logger", _DeadLogger())
    service = LLMService(enabled=True, provider=FakeProvider(_VALID))
    out, _ = service.generate_explanation(_evidence())
    assert out.summary == "Anomalous flow observed."


# 11/12. Consistent names across repeats; failure excludes completion.
def test_repeated_requests_consistent(make_store, fake_embedder):
    rag = _rag(make_store, fake_embedder)
    rag.query("scanning open ports")
    rag.query("scanning open ports")
    snap = obs.get_snapshot()
    assert snap["events"][obs.RAG_QUERY_ATTEMPTED] == {obs.CATEGORY_OK: 2}
    assert snap["events"][obs.RAG_QUERY_COMPLETED] == {obs.CATEGORY_OK: 2}
    assert set(snap["events"]) <= {
        obs.RAG_QUERY_ATTEMPTED, obs.RAG_QUERY_COMPLETED,
        obs.RAG_PROVENANCE_UNKNOWN,
    }
