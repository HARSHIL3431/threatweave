import pytest
from unittest.mock import Mock


def test_detect_single_benign_flow(client, sample_flows):
    """Verify single flow detection for a known benign sample."""
    payload = sample_flows["benign_flow"]["input"]
    response = client.post(
        "/api/v1/detect",
        json=payload,
        headers={"X-Correlation-ID": "test-req-123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["request_id"] == "test-req-123"
    assert data["detection"]["is_anomaly"] is False
    assert data["detection"]["experiment_id"] == "with_port"
    assert data["detection"]["threshold"] == pytest.approx(0.521919, abs=1e-5)
    assert data["severity"]["level"] in ("info", "low")
    assert data["attack_context"]["mitre_techniques"] == []
    assert data["explanation"]["recommendations"] == []
    assert data["metadata"]["model_version"] == "isolation_forest_v1"


def test_detect_single_anomalous_flow(client, sample_flows):
    """Verify single flow detection for a known anomalous sample."""
    payload = sample_flows["anomalous_flow"]["input"]
    response = client.post("/api/v1/detect", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["detection"]["is_anomaly"] is True
    assert data["detection"]["anomaly_score"] >= data["detection"]["threshold"]
    assert data["severity"]["level"] in ("medium", "high", "critical")


def test_detect_batch_flows(client, sample_flows):
    """Verify batch flow detection preserves ordering and handles multiple flows."""
    flows = [
        sample_flows["benign_flow"]["input"],
        sample_flows["anomalous_flow"]["input"],
        sample_flows["zero_duration_flow"]["input"],
    ]
    response = client.post(
        "/api/v1/detect/batch",
        json={"flows": flows},
        headers={"X-Correlation-ID": "batch-corr-999"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"] == "batch-corr-999"
    assert data["count"] == 3
    assert len(data["results"]) == 3
    
    # Check ordering
    assert data["results"][0]["detection"]["is_anomaly"] is False
    assert data["results"][1]["detection"]["is_anomaly"] is True
    assert data["results"][2]["detection"]["is_anomaly"] is False


def test_detect_empty_batch(client):
    """Verify empty batch returns empty result set."""
    response = client.post("/api/v1/detect/batch", json={"flows": []})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["results"] == []


def test_detect_missing_features_error(client, sample_flows):
    """Verify missing required features returns 422 with structured ErrorResponse."""
    payload = dict(sample_flows["benign_flow"]["input"])
    del payload["Destination Port"]
    del payload["Flow Duration"]
    
    response = client.post("/api/v1/detect", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "INVALID_INPUT"
    assert "validation_errors" in data["details"]


def test_detect_nan_inf_rejected(client, sample_flows):
    """Verify NaN/Inf numeric values return 422 structured error."""
    # Test string NaN in JSON
    payload = dict(sample_flows["benign_flow"]["input"])
    payload["Flow Duration"] = "NaN"
    response = client.post("/api/v1/detect", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error_code"] == "INVALID_INPUT"


def test_detect_when_model_not_ready(sample_flows):
    """Verify 503 MODEL_NOT_READY structured error when ML model is unavailable."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import get_ml_service
    from app.services.ml_service import MLService
    
    unloaded_svc = MLService()
    app.dependency_overrides[get_ml_service] = lambda: unloaded_svc
    with TestClient(app) as client:
        payload = sample_flows["benign_flow"]["input"]
        response = client.post("/api/v1/detect", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert data["error_code"] == "MODEL_NOT_READY"
        assert "unavailable" in data["message"].lower() or "not been loaded" in data["message"].lower()
    app.dependency_overrides.clear()


def test_inference_failure_returns_safe_structured_error(sample_flows):
    """Model exceptions become a generic structured API error without leakage."""
    from app.dependencies import get_ml_service
    from app.main import app
    from app.services.ml_service import MLService

    failing_service = MLService()
    failing_service.load_artifacts()
    failing_service.model.score_samples = Mock(
        side_effect=RuntimeError("internal model path and secret details")
    )
    app.dependency_overrides[get_ml_service] = lambda: failing_service

    try:
        from fastapi.testclient import TestClient
        with TestClient(app) as failing_client:
            response = failing_client.post(
                "/api/v1/detect",
                json=sample_flows["benign_flow"]["input"],
                headers={"X-Correlation-ID": "inference-failure"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    data = response.json()
    assert data["error_code"] == "INFERENCE_ERROR"
    assert data["message"] == "An error occurred during anomaly inference"
    assert data["request_id"] == "inference-failure"
    assert "internal model path" not in response.text
    assert "secret details" not in response.text

