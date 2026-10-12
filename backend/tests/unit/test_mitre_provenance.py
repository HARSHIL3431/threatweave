"""P0-1 tests: MITRE provenance persistence and honest age reporting.

Fully offline: FakeEmbedder/make_store fixtures only, fixed clock, no
MiniLM or MITRE downloads, no network access.
"""
import hashlib
import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.dependencies import get_rag_service_public
from app.main import app
from app.services.mitre_provenance import (
    STALE_AFTER_DAYS,
    compute_provenance,
    extract_attack_version,
    knowledge_age,
)
from app.services.rag_service import RagService, clear_rag_cache
from app.services.vector_store import VectorStore

FIXED_NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
SOURCE_URL = "https://example.invalid/enterprise-attack.json"


def _bundle():
    return {
        "type": "bundle",
        "id": "bundle--test",
        "spec_version": "2.0",
        "objects": [
            {
                "id": "attack-pattern--a",
                "type": "attack-pattern",
                "name": "Alpha",
                "modified": "2026-08-04T20:30:56.386Z",
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "T1000"}
                ],
            },
            {
                "id": "attack-pattern--b",
                "type": "attack-pattern",
                "name": "Beta",
                "modified": "2026-01-02T00:00:00Z",
                "external_references": [
                    {"source_name": "mitre-attack", "external_id": "T2000"}
                ],
            },
            {"id": "malware--x", "type": "malware", "name": "Ignored"},
        ],
    }


def _provenance(built_at=None):
    bundle = _bundle()
    raw = json.dumps(bundle).encode("utf-8")
    return compute_provenance(
        source_url=SOURCE_URL,
        bundle_bytes=raw,
        bundle=json.loads(raw.decode("utf-8")),
        built_at=built_at or FIXED_NOW,
    )


def _docs():
    return [
        {
            "text": "Technique: Alpha (T1000)\nDescription: first",
            "meta": {
                "technique_id": "T1000",
                "technique_name": "Alpha",
                "type": "technique",
                "tactics": [],
                "description": "first",
                "detection": None,
                "mitigations": [],
                "data_sources": [],
                "platforms": [],
            },
        },
    ]


def _store_with_provenance(make_store, provenance):
    index_path, metadata_path = make_store(_docs())
    store = VectorStore.load(index_path, metadata_path)
    store.provenance = provenance
    store.save()
    clear_rag_cache()
    return index_path, metadata_path


# 1. Newly generated provenance contains all required fields.
def test_provenance_contains_all_required_fields():
    prov = _provenance()
    for key in (
        "source_url",
        "bundle_sha256",
        "bundle_bytes",
        "attack_pattern_count",
        "max_modified",
        "built_at",
    ):
        assert key in prov, f"missing provenance field: {key}"
    assert prov["source_url"] == SOURCE_URL
    assert prov["attack_pattern_count"] == 2
    assert prov["max_modified"] is not None
    assert prov["built_at"] is not None


# 2. SHA-256 and byte count match the exact source bytes.
def test_provenance_hash_and_size_match_source_bytes():
    bundle = _bundle()
    raw = json.dumps(bundle).encode("utf-8")
    prov = compute_provenance(
        source_url=SOURCE_URL,
        bundle_bytes=raw,
        bundle=json.loads(raw.decode("utf-8")),
        built_at=FIXED_NOW,
    )
    assert prov["bundle_sha256"] == hashlib.sha256(raw).hexdigest()
    assert prov["bundle_bytes"] == len(raw)
    assert len(prov["bundle_sha256"]) == 64


# 3. Missing release metadata is represented honestly.
def test_missing_release_metadata_is_honest():
    assert extract_attack_version(_bundle()) is None
    assert _provenance()["attack_version"] is None
    bare = {"type": "bundle", "id": "bundle--bare", "objects": []}
    raw = json.dumps(bare).encode("utf-8")
    prov = compute_provenance(
        source_url=SOURCE_URL, bundle_bytes=raw, bundle=bare, built_at=FIXED_NOW
    )
    assert prov["attack_version"] is None
    assert prov["max_modified"] is None
    assert prov["attack_pattern_count"] == 0


# 4. An existing metadata file without provenance still loads.
def test_legacy_metadata_without_provenance_loads(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs())
    loaded = VectorStore.load(index_path, metadata_path)
    assert loaded.provenance is None
    clear_rag_cache()
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )
    status = rag.status(now=FIXED_NOW)
    assert status["status"] == "ready"
    assert status["built_at"] is None
    assert status["attack_version"] is None
    assert status["knowledge_age_days"] is None
    assert status["knowledge_age_status"] == "unknown"
    assert status["is_stale"] is False


# 5. The RAG status endpoint returns provenance when available.
def test_status_endpoint_returns_provenance(make_store, fake_embedder):
    prov = _provenance()
    index_path, metadata_path = _store_with_provenance(make_store, prov)
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/rag/status")
    finally:
        app.dependency_overrides.clear()
        clear_rag_cache()
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["source_url"] == SOURCE_URL
    assert data["bundle_sha256"] == prov["bundle_sha256"]
    assert data["bundle_bytes"] == prov["bundle_bytes"]
    assert data["attack_pattern_count"] == 2
    assert data["built_at"] == prov["built_at"]
    assert data["knowledge_age_status"] in ("fresh", "stale")
    assert isinstance(data["is_stale"], bool)


# 6. Missing or invalid timestamps yield an unknown age, not false fresh.
def test_missing_or_invalid_timestamps_yield_unknown_age():
    for bad in (None, "", "   ", "not-a-date", 12345, "2026-13-99T99:99:99Z"):
        age = knowledge_age(bad, now=FIXED_NOW)
        assert age == {"age_days": None, "age_status": "unknown", "is_stale": False}


# 7. A valid timestamp older than 180 days is reported as stale.
def test_old_timestamp_is_stale(make_store, fake_embedder):
    age = knowledge_age("2025-01-01T00:00:00+00:00", now=FIXED_NOW)
    assert age["age_days"] is not None and age["age_days"] > STALE_AFTER_DAYS
    assert age["age_status"] == "stale"
    assert age["is_stale"] is True

    prov = _provenance(built_at=datetime(2025, 1, 1, tzinfo=timezone.utc))
    index_path, metadata_path = _store_with_provenance(make_store, prov)
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )
    status = rag.status(now=FIXED_NOW)
    assert status["knowledge_age_status"] == "stale"
    assert status["is_stale"] is True
    clear_rag_cache()


# 8. A recent valid timestamp is not reported as stale.
def test_recent_timestamp_is_not_stale(make_store, fake_embedder):
    age = knowledge_age("2026-10-01T00:00:00+00:00", now=FIXED_NOW)
    assert age["age_status"] == "fresh"
    assert age["is_stale"] is False
    assert age["age_days"] == 10

    # Exactly 180 days is the boundary: only *more than* 180 is stale.
    boundary = knowledge_age("2026-04-14T12:00:00+00:00", now=FIXED_NOW)
    assert boundary["age_days"] == 180
    assert boundary["is_stale"] is False

    prov = _provenance()
    index_path, metadata_path = _store_with_provenance(make_store, prov)
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )
    status = rag.status(now=FIXED_NOW)
    assert status["knowledge_age_status"] == "fresh"
    assert status["is_stale"] is False
    clear_rag_cache()


# 9. Existing RAG status fields and behavior remain compatible.
def test_existing_status_fields_compatible(make_store, fake_embedder):
    prov = _provenance()
    index_path, metadata_path = _store_with_provenance(make_store, prov)
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )
    status = rag.status(now=FIXED_NOW)
    assert status["status"] == "ready"
    assert status["embedding_model"] == "fake-model"
    assert status["embedding_dim"] == 8
    assert status["doc_count"] == 1
    assert isinstance(status["index_path"], str)
    # Retrieval still works against a provenance-carrying index.
    hits = rag.query("Alpha first", top_k=5)
    assert [h.technique_id for h in hits] == ["T1000"]
    clear_rag_cache()


# 10. No status request triggers a network download or index rebuild.
def test_status_triggers_no_network_or_rebuild(make_store, fake_embedder):
    prov = _provenance()
    index_path, metadata_path = _store_with_provenance(make_store, prov)

    class _NoEmbed:
        def embed(self, texts, batch_size=32):
            raise AssertionError("status() must not embed or rebuild")

    before_index = index_path.stat().st_mtime_ns
    before_meta = metadata_path.stat().st_mtime_ns
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=_NoEmbed(),
    )
    first = rag.status(now=FIXED_NOW)
    second = rag.status(now=FIXED_NOW)
    assert first["status"] == "ready" and second["status"] == "ready"
    assert index_path.stat().st_mtime_ns == before_index
    assert metadata_path.stat().st_mtime_ns == before_meta
    clear_rag_cache()
