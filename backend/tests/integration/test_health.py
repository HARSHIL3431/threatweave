def test_health_endpoint_healthy(client):
    """Verify health endpoint returns 200 and model status ready."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_status"] == "ready"
    assert data["experiment_id"] == "with_port"
    assert data["model_version"] == "isolation_forest_v1"
    assert data["active_operating_point"] == "OP-A"
    assert data["active_threshold"] > 0
    assert "timestamp" in data


def test_health_when_model_not_ready():
    """Verify health endpoint returns degraded status when model is not ready."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import get_ml_service
    from app.services.ml_service import MLService
    
    unloaded_svc = MLService()
    app.dependency_overrides[get_ml_service] = lambda: unloaded_svc
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["model_status"] == "not_loaded"
    app.dependency_overrides.clear()


def test_openapi_exposes_required_backend_routes(client):
    """Verify the documented API surface remains available for frontend integration."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/detect" in paths
    assert "/api/v1/detect/batch" in paths
    assert "get" in paths["/api/v1/health"]
    assert "post" in paths["/api/v1/detect"]
    assert "post" in paths["/api/v1/detect/batch"]

