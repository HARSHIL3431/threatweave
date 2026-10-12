"""P0-2 tests: FAISS index and metadata integrity (fail closed, offline).

Uses temporary directories, small synthetic FAISS indexes, and synthetic
metadata fixtures. Never touches the production index or the network.
"""
import json

import faiss
import numpy as np
import pytest

from app.core.exceptions import RagUnavailableException
from app.services.rag_service import RagService, clear_rag_cache
from app.services.vector_store import VectorStore, VectorStoreIntegrityError


def _vecs(n, dim=8, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.random((n, dim)).astype("float32")
    if n:
        v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v


def _doc(tid="T-TEST-1", name="Alpha", dtype="technique"):
    return {
        "technique_id": tid,
        "technique_name": name,
        "type": dtype,
        "tactics": [],
        "description": "synthetic",
        "detection": None,
        "mitigations": [],
        "data_sources": [],
        "platforms": [],
    }


def _meta(docs, dim=8, **overrides):
    base = {
        "embedding_model": "fake-model",
        "dimension": dim,
        "doc_count": len(docs),
        "technique_count": sum(
            1 for d in docs if isinstance(d, dict) and d.get("type") == "technique"
        ),
        "subtechnique_count": sum(
            1
            for d in docs
            if isinstance(d, dict) and d.get("type") == "sub-technique"
        ),
        "created_at": "2026-10-11T00:00:00+00:00",
        "documents": docs,
    }
    base.update(overrides)
    return base


def _write_pair(tmp_path, vectors, meta, name="vs"):
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    index_path = d / "index.faiss"
    metadata_path = d / "metadata.json"
    arr = np.asarray(vectors, dtype="float32")
    index = faiss.IndexFlatIP(arr.shape[1])
    if len(arr):
        index.add(arr)
    faiss.write_index(index, str(index_path))
    metadata_path.write_text(json.dumps(meta), encoding="utf-8")
    return index_path, metadata_path


def _service(index_path, metadata_path, fake_embedder):
    return RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )


# 1. Valid index and matching metadata load successfully.
def test_valid_pair_loads(tmp_path):
    docs = [_doc("T-TEST-1", "Alpha"), _doc("T-TEST-2", "Beta", "sub-technique")]
    index_path, metadata_path = _write_pair(tmp_path, _vecs(2), _meta(docs))
    store = VectorStore.load(index_path, metadata_path)
    assert store.index.ntotal == 2
    assert store.dimension == 8
    assert len(store.documents) == 2
    assert store.provenance is None


# 2. Valid empty index follows the intended empty-index behavior.
def test_valid_empty_pair_loads_and_searches_empty(tmp_path, fake_embedder):
    index_path, metadata_path = _write_pair(tmp_path, _vecs(0, dim=8), _meta([]))
    store = VectorStore.load(index_path, metadata_path)
    assert store.index.ntotal == 0
    assert store.search(np.zeros(8, dtype="float32")) == []
    rag = _service(index_path, metadata_path, fake_embedder)
    try:
        assert rag.status()["status"] == "ready"
        assert rag.status()["doc_count"] == 0
        assert rag.query("anything", top_k=3) == []
    finally:
        clear_rag_cache()


# 3. Missing index file is handled correctly.
def test_missing_index_file(tmp_path, fake_embedder):
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(_meta([_doc()])), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        VectorStore.load(tmp_path / "absent.faiss", metadata_path)
    rag = _service(tmp_path / "absent.faiss", metadata_path, fake_embedder)
    try:
        assert rag.status()["status"] == "unavailable"
        with pytest.raises(RagUnavailableException):
            rag.query("anything", top_k=1)
    finally:
        clear_rag_cache()


# 4. Missing metadata file is handled correctly.
def test_missing_metadata_file(tmp_path, fake_embedder):
    index_path, _ = _write_pair(tmp_path, _vecs(1), _meta([_doc()]))
    with pytest.raises(FileNotFoundError):
        VectorStore.load(index_path, tmp_path / "vs" / "absent.json")
    rag = _service(index_path, tmp_path / "vs" / "absent.json", fake_embedder)
    try:
        assert rag.status()["status"] == "unavailable"
    finally:
        clear_rag_cache()


# 5. Malformed metadata JSON or unsupported structure is rejected.
@pytest.mark.parametrize(
    "payload",
    [
        "{not valid json",
        "[1, 2, 3]",
        '"just a string"',
    ],
)
def test_malformed_metadata_rejected(tmp_path, payload):
    index_path, metadata_path = _write_pair(tmp_path, _vecs(1), _meta([_doc()]))
    metadata_path.write_text(payload, encoding="utf-8")
    with pytest.raises(VectorStoreIntegrityError):
        VectorStore.load(index_path, metadata_path)


def test_non_list_documents_rejected(tmp_path):
    index_path, metadata_path = _write_pair(
        tmp_path, _vecs(1), _meta([_doc()], documents={"0": _doc()})
    )
    with pytest.raises(VectorStoreIntegrityError):
        VectorStore.load(index_path, metadata_path)


# 6. Vector count and mapped document count mismatch is rejected.
@pytest.mark.parametrize("n_docs", [1, 3])
def test_count_mismatch_rejected(tmp_path, fake_embedder, n_docs):
    docs = [_doc(f"T-TEST-{i}", f"Name {i}") for i in range(n_docs)]
    index_path, metadata_path = _write_pair(tmp_path, _vecs(2), _meta(docs))
    with pytest.raises(VectorStoreIntegrityError):
        VectorStore.load(index_path, metadata_path)
    rag = _service(index_path, metadata_path, fake_embedder)
    try:
        status = rag.status()
        assert status["status"] == "unavailable"
        assert "integrity" in status.get("detail", "").lower()
        with pytest.raises(RagUnavailableException):
            rag.query("anything", top_k=1)
    finally:
        clear_rag_cache()


# 7. Invalid or duplicate identifiers are handled explicitly.
@pytest.mark.parametrize(
    "docs",
    [
        # missing technique_id
        [{k: v for k, v in _doc().items() if k != "technique_id"}],
        # blank technique_id
        [_doc(tid="  ")],
        # missing technique_name
        [{k: v for k, v in _doc().items() if k != "technique_name"}],
        # unknown type
        [_doc(dtype="malware")],
        # non-object record
        ["not-a-dict"],
        # duplicate identifiers (counts kept aligned so only dup fires)
        [_doc("T-DUP", "One"), _doc("T-DUP", "Two")],
    ],
)
def test_invalid_or_duplicate_identifiers_rejected(tmp_path, docs):
    n = len(docs)
    index_path, metadata_path = _write_pair(tmp_path, _vecs(n), _meta(docs))
    with pytest.raises(VectorStoreIntegrityError):
        VectorStore.load(index_path, metadata_path)


# 8. Wrong embedding dimension is rejected.
def test_stored_dimension_mismatch_rejected(tmp_path):
    index_path, metadata_path = _write_pair(
        tmp_path, _vecs(1), _meta([_doc()], dimension=16)
    )
    with pytest.raises(VectorStoreIntegrityError):
        VectorStore.load(index_path, metadata_path)


def test_wrong_query_dimension_rejected(tmp_path):
    index_path, metadata_path = _write_pair(tmp_path, _vecs(1), _meta([_doc()]))
    store = VectorStore.load(index_path, metadata_path)
    with pytest.raises(ValueError):
        store.search(np.zeros(4, dtype=np.float32))


# 9. Unmapped FAISS positions cannot return unrelated techniques.
def test_unmapped_positions_never_resolve(tmp_path, fake_embedder):
    vectors = fake_embedder.embed(["alpha technique", "beta technique"])
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(np.asarray(vectors, dtype=np.float32))
    # Direct construction bypassing load: only one document mapped.
    store = VectorStore(
        index=index,
        documents=[_doc("T-ONLY", "Only")],
        dimension=vectors.shape[1],
        embedding_model="fake-model",
        index_path=tmp_path / "index.faiss",
        metadata_path=tmp_path / "metadata.json",
    )
    hits = store.search(fake_embedder.embed(["alpha technique"]), top_k=5)
    assert all(h["technique_id"] == "T-ONLY" for h in hits)
    assert len(hits) <= 1


# 10. Legitimate legacy metadata remains compatible.
def test_legacy_metadata_without_provenance_loads(tmp_path):
    docs = [_doc("T1001", "Data Obfuscation"), _doc("T1001.001", "Sub", "sub-technique")]
    legacy = {
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 8,
        "doc_count": 2,
        "technique_count": 1,
        "subtechnique_count": 1,
        "created_at": "2026-09-20T16:30:42+00:00",
        "documents": docs,
    }
    assert "provenance" not in legacy
    index_path, metadata_path = _write_pair(tmp_path, _vecs(2), legacy)
    store = VectorStore.load(index_path, metadata_path)
    assert store.provenance is None
    assert len(store.documents) == 2


# 11. P0-1 provenance fields survive loading and saving without alteration.
def test_provenance_survives_roundtrip(make_store):
    prov = {
        "source_url": "https://example.invalid/enterprise-attack.json",
        "bundle_sha256": "ab" * 32,
        "bundle_bytes": 1234,
        "attack_pattern_count": 2,
        "attack_version": None,
        "max_modified": "2026-08-04T20:30:56+00:00",
        "built_at": "2026-10-11T00:00:00+00:00",
    }
    docs = [
        {
            "text": "Technique: Alpha (T-TEST-1)",
            "meta": _doc("T-TEST-1", "Alpha"),
        },
        {
            "text": "Technique: Beta (T-TEST-2)",
            "meta": _doc("T-TEST-2", "Beta"),
        },
    ]
    index_path, metadata_path = make_store(docs)
    store = VectorStore.load(index_path, metadata_path)
    store.provenance = prov
    store.save()
    reloaded = VectorStore.load(index_path, metadata_path)
    assert reloaded.provenance == prov
    clear_rag_cache()


# 12. Corrupted artifacts never report a healthy/ready status.
@pytest.mark.parametrize("corrupt", ["garbage", "truncated"])
def test_corrupted_artifacts_never_ready(tmp_path, fake_embedder, corrupt):
    index_path, metadata_path = _write_pair(tmp_path, _vecs(2), _meta([_doc(), _doc("T-TEST-2", "Beta")]))
    raw = index_path.read_bytes()
    if corrupt == "garbage":
        index_path.write_bytes(b"not-a-faiss-index" * 64)
    else:
        index_path.write_bytes(raw[: max(16, len(raw) // 3)])
    with pytest.raises(Exception):
        VectorStore.load(index_path, metadata_path)
    rag = _service(index_path, metadata_path, fake_embedder)
    try:
        status = rag.status()
        assert status["status"] == "unavailable"
        assert status["status"] != "ready"
        with pytest.raises(RagUnavailableException):
            rag.query("anything", top_k=1)
        # Detection-time retrieval degrades to [] instead of wrong data.
        assert rag.retrieve_context({"Destination Port": 80}, 0.9) == []
    finally:
        clear_rag_cache()


# 13. Existing valid search and RAG behavior remains unchanged.
def test_valid_search_behavior_unchanged(make_store, fake_embedder):
    docs = [
        {
            "text": "Technique: Port Scanning (T-TEST-1)\nTactics: discovery\nDescription: Scan open ports on a host",
            "meta": _doc("T-TEST-1", "Port Scanning"),
        },
        {
            "text": "Technique: Phishing (T-TEST-2)\nDescription: Send deceptive email",
            "meta": _doc("T-TEST-2", "Phishing"),
        },
    ]
    index_path, metadata_path = make_store(docs)
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
        top_k=5,
    )
    try:
        hits = rag.query("Scan open ports on a host scanning")
        assert [h.technique_id for h in hits] == ["T-TEST-1", "T-TEST-2"]
        assert hits[0].score >= hits[1].score
        context = rag.retrieve_context({"Destination Port": 80}, 0.9)
        assert len(context) == 2
        assert all("retrieved-not-confirmed" in c for c in context)
    finally:
        clear_rag_cache()
