"""Integration tests for the RAG API endpoints and detection coexistence."""
import pytest
from fastapi.testclient import TestClient

from app.dependencies import (
    get_detection_service,
    get_rag_service_public,
)
from app.main import app
from app.services.detection_service import DetectionService
from app.services.llm_service import LLMService
from app.services.mitre_service import MitreService
from app.services.rag_service import RagService


def _docs():
    return [
        {
            "text": "Technique: Network Service Discovery (T-TEST-1)\nTactics: discovery\nDescription: Scan open ports",
            "meta": {
                "technique_id": "T-TEST-1",
                "technique_name": "Network Service Discovery",
                "type": "technique",
                "tactics": ["discovery"],
                "description": "Scan open ports",
                "detection": "Watch for repeated connections",
                "mitigations": [],
                "data_sources": [],
                "platforms": [],
            },
        },
        {
            "text": "Technique: Credential Dumping (T-TEST-2)\nTactics: credential-access\nDescription: Extract credentials",
            "meta": {
                "technique_id": "T-TEST-2",
                "technique_name": "Credential Dumping",
                "type": "technique",
                "tactics": ["credential-access"],
                "description": "Extract credentials",
                "detection": "Monitor memory access",
                "mitigations": ["M-PRIV"],
                "data_sources": [],
                "platforms": [],
            },
        },
    ]


def _rag_for(make_store, tmp_path, fake_embedder):
    index_path, metadata_path = make_store(_docs())
    return RagService(
        enabled=True,
        index_path=index_path,
        metadata_path=metadata_path,
        embedder=fake_embedder,
        top_k=5,
    )


def test_openapi_exposes_rag_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/rag/query" in paths
    assert "/api/v1/rag/status" in paths
    assert "post" in paths["/api/v1/rag/query"]
    assert "get" in paths["/api/v1/rag/status"]


def test_rag_query_endpoint_returns_grounded_results(make_store, tmp_path, fake_embedder):
    rag = _rag_for(make_store, tmp_path, fake_embedder)
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rag/query",
                json={"query": "scanning open ports", "top_k": 2},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "scanning open ports"
    assert data["top_k"] == 2
    assert data["result_count"] == 2
    assert "retrieval_time_ms" in data
    first = data["results"][0]
    assert first["technique_id"] == "T-TEST-1"
    assert first["technique_name"] == "Network Service Discovery"
    assert first["tactics"] == ["discovery"]
    assert "score" in first and 0.0 <= first["score"] <= 1.0
    assert first["technique_type"] == "technique"


def test_rag_query_default_top_k_and_score_ordering(make_store, tmp_path, fake_embedder):
    rag = _rag_for(make_store, tmp_path, fake_embedder)
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/rag/query", json={"query": "scanning open ports"})
    finally:
        app.dependency_overrides.clear()

    data = response.json()
    assert data["top_k"] == 5
    assert data["result_count"] == 2
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize("payload", [{"query": ""}, {"query": "   "}])
def test_rag_query_empty_query_returns_422(make_store, tmp_path, fake_embedder, payload):
    rag = _rag_for(make_store, tmp_path, fake_embedder)
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/rag/query", json={**payload, "top_k": 5})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["error_code"] == "INVALID_INPUT"


@pytest.mark.parametrize("top_k", [0, 51])
def test_rag_query_top_k_out_of_bounds_422(make_store, tmp_path, fake_embedder, top_k):
    rag = _rag_for(make_store, tmp_path, fake_embedder)
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/rag/query", json={"query": "scanning", "top_k": top_k}
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_rag_status_ready(make_store, tmp_path, fake_embedder):
    rag = _rag_for(make_store, tmp_path, fake_embedder)
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/rag/status")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["doc_count"] == 2
    assert data["embedding_model"] == "fake-model"
    assert data["embedding_dim"] == 8


def test_rag_missing_index_returns_503_and_clear_error(tmp_path, fake_embedder):
    rag = RagService(
        enabled=True,
        index_path=tmp_path / "missing" / "index.faiss",
        metadata_path=tmp_path / "missing" / "metadata.json",
        embedder=fake_embedder,
    )
    app.dependency_overrides[get_rag_service_public] = lambda: rag
    try:
        with TestClient(app) as client:
            status_resp = client.get("/api/v1/rag/status")
            query_resp = client.post("/api/v1/rag/query", json={"query": "anything"})
    finally:
        app.dependency_overrides.clear()

    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "unavailable"

    assert query_resp.status_code == 503
    data = query_resp.json()
    assert data["error_code"] == "RAG_UNAVAILABLE"


def test_detection_still_works_when_rag_and_mitre_unavailable(
    loaded_ml_service, sample_flows, tmp_path, fake_embedder
):
    """RAG/MITRE failures must never break ML anomaly detection."""
    rag = RagService(
        enabled=True,
        index_path=tmp_path / "missing" / "index.faiss",
        metadata_path=tmp_path / "missing" / "metadata.json",
        embedder=fake_embedder,
    )
    mitre = MitreService(enabled=True, rag_service=rag)

    app.dependency_overrides[get_detection_service] = lambda: DetectionService(
        ml_service=loaded_ml_service,
        mitre_service=mitre,
        rag_service=rag,
        llm_service=LLMService(),
    )
    try:
        with TestClient(app) as client:
            payload = sample_flows["anomalous_flow"]["input"]
            response = client.post("/api/v1/detect", json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["detection"]["is_anomaly"] is True
    assert data["attack_context"]["mitre_techniques"] == []
    assert data["attack_context"]["retrieved_context"] == []


def test_rag_service_initialization_defaults():
    """RagService matches settings without requiring a model download."""
    rag = RagService()
    assert rag.enabled is False
    assert rag.top_k == 5
    assert str(rag.index_path) == str(app_settings_mitre_index())
    assert rag.status()["status"] in ("ready", "unavailable")


def app_settings_mitre_index():
    from app.core.config import settings

    return settings.mitre_index_file