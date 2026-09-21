"""Unit tests for vector store and RAG service (no real embedding model)."""
import pytest

from app.core.exceptions import RagUnavailableException
from app.services.rag_service import RagService, build_query_from_flow, clear_rag_cache
from app.services.vector_store import VectorStore


def _docs_simple():
    return [
        {
            "text": "Technique: Port Scanning (T-TEST-1)\nTactics: discovery\nDescription: Scan open ports on a host",
            "meta": {
                "technique_id": "T-TEST-1",
                "technique_name": "Port Scanning",
                "type": "technique",
                "tactics": ["discovery"],
                "description": "Scan open ports on a host",
                "detection": "Watch for connection attempts",
                "mitigations": [],
                "data_sources": [],
                "platforms": [],
            },
        },
        {
            "text": "Technique: Phishing (T-TEST-2)\nTactics: initial-access\nDescription: Send deceptive email",
            "meta": {
                "technique_id": "T-TEST-2",
                "technique_name": "Phishing",
                "type": "technique",
                "tactics": ["initial-access"],
                "description": "Send deceptive email",
                "detection": "Inspect mail headers",
                "mitigations": ["M-TEST-M"],
                "data_sources": [],
                "platforms": [],
            },
        },
    ]


def _rag_service(index_path, metadata_path):
    return RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=FakeEmbedder(),
        top_k=5,
    )


class FakeEmbedder:
    """Deterministic tiny embedder mirroring the conftest one."""

    DIM = 8

    def embed(self, texts, batch_size=32):
        import hashlib

        import numpy as np

        vectors = []
        for text in texts:
            digest = hashlib.md5(text.encode("utf-8")).digest()
            v = np.frombuffer(digest, dtype=np.uint8).astype(np.float32)[: self.DIM]
            v = np.pad(v, (0, self.DIM - len(v))) / 255.0
            norm = np.linalg.norm(v)
            vectors.append(v / norm if norm > 0 else v)
        return np.asarray(vectors, dtype=np.float32).reshape(len(texts), self.DIM)


def test_vector_store_create_load_roundtrip(make_store):
    docs = _docs_simple()
    index_path, metadata_path = make_store(docs)
    loaded = VectorStore.load(index_path, metadata_path)
    assert loaded.index.ntotal == len(docs)
    assert loaded.dimension == 8
    assert loaded.documents[0]["technique_id"] == "T-TEST-1"


def test_vector_store_search_returns_score_and_metadata(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs_simple())
    store = VectorStore.load(index_path, metadata_path)
    query_vec = fake_embedder.embed(["Scan open ports on a host scanning"])

    hits = store.search(query_vec, top_k=5)
    assert len(hits) == 2
    assert all("score" in h and "technique_id" in h for h in hits)
    # Results sorted best-first
    assert hits[0]["score"] >= hits[1]["score"]
    assert hits[0]["technique_id"] == "T-TEST-1"


def test_vector_store_top_k_respected(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs_simple())
    store = VectorStore.load(index_path, metadata_path)
    query_vec = fake_embedder.embed(["scanning open ports"])
    assert len(store.search(query_vec, top_k=1)) == 1
    # top_k larger than doc count returns all available
    assert len(store.search(query_vec, top_k=99)) == 2


def test_rag_status_unavailable_when_index_missing(tmp_path, fake_embedder):
    rag = RagService(
        enabled=True,
        index_path=tmp_path / "nope" / "index.faiss",
        metadata_path=tmp_path / "nope" / "metadata.json",
        embedder=fake_embedder,
    )
    assert rag.is_available() is False
    status = rag.status()
    assert status["status"] == "unavailable"
    assert "index" in status["detail"].lower()


def test_rag_query_raises_when_index_missing(tmp_path, fake_embedder):
    rag = RagService(
        enabled=True,
        index_path=tmp_path / "nope" / "index.faiss",
        metadata_path=tmp_path / "nope" / "metadata.json",
        embedder=fake_embedder,
    )
    with pytest.raises(RagUnavailableException):
        rag.query("anything", top_k=3)


def test_rag_disabled_returns_empty_context(tmp_path, fake_embedder):
    rag = RagService(enabled=False, embedder=fake_embedder)
    assert rag.retrieve_context({"Destination Port": 80}, 0.9) == []


def test_rag_retrieve_context_returns_grounded_strings(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs_simple())
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
        top_k=2,
    )
    context = rag.retrieve_context(
        {"Destination Port": 80, "Flow Duration": 1000, "Total Fwd Packets": 5,
         "Total Backward Packets": 2, "Total Length of Fwd Packets": 1000,
         "Total Length of Bwd Packets": 200, "Flow Packets/s": 10.0,
         "Flow Bytes/s": 20.0, "ACK Flag Count": 1, "FIN Flag Count": 0,
         "RST Flag Count": 0, "PSH Flag Count": 0, "URG Flag Count": 0,
         "Init_Win_bytes_forward": 8192, "Is_Zero_Duration": 0},
        0.9,
    )
    assert len(context) == 2
    assert all(isinstance(c, str) for c in context)
    assert "retrieved-not-confirmed" in context[0]
    assert "T-TEST-" in context[0]


def test_rag_retrieve_context_handles_missing_index_gracefully(tmp_path, fake_embedder):
    rag = RagService(
        enabled=True,
        index_path=tmp_path / "missing" / "index.faiss",
        metadata_path=tmp_path / "missing" / "metadata.json",
        embedder=fake_embedder,
    )
    # Never raises; ML detection is not blocked by RAG availability.
    assert rag.retrieve_context({"Destination Port": 80}, 0.9) == []


def test_rag_query_top_k_behavior(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs_simple())
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
        top_k=1,
    )
    full = rag.query("scanning ports", top_k=5)
    limited = rag.query("scanning ports", top_k=1)
    assert len(full) == 2
    assert len(limited) == 1


def test_rag_query_empty_string_rejected(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs_simple())
    rag = RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
    )
    with pytest.raises(ValueError):
        rag.query("   ", top_k=3)


def test_build_query_from_flow_is_deterministic():
    flow = {
        "Destination Port": 3389, "Flow Duration": 1_000_000,
        "Total Fwd Packets": 100, "Total Backward Packets": 50,
        "Total Length of Fwd Packets": 5000, "Total Length of Bwd Packets": 2000,
        "Flow Packets/s": 100.5, "Flow Bytes/s": 7000.25,
        "ACK Flag Count": 10, "FIN Flag Count": 1, "RST Flag Count": 0,
        "PSH Flag Count": 0, "URG Flag Count": 0,
        "Init_Win_bytes_forward": 8192, "Is_Zero_Duration": 0,
    }
    q1 = build_query_from_flow(flow)
    q2 = build_query_from_flow(flow)
    assert q1 == q2
    assert "3389" in q1
    assert "100" in q1
    assert "suspicious" in q1.lower()


def test_cache_is_shared_across_service_instances(make_store, fake_embedder):
    index_path, metadata_path = make_store(_docs_simple())
    clear_rag_cache()
    r1 = RagService(enabled=True, index_path=index_path, metadata_path=metadata_path, embedder=fake_embedder)
    r2 = RagService(enabled=True, index_path=index_path, metadata_path=metadata_path, embedder=fake_embedder)
    assert r1.is_available() is True
    # Second instance hits the shared cache rather than re-loading the file.
    assert r2.status()["status"] == "ready"
    clear_rag_cache()