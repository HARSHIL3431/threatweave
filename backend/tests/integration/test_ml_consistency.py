import pytest
import numpy as np
from app.services.ml_service import MLService


def test_frozen_pipeline_vs_backend_consistency(client, sample_flows, loaded_ml_service):
    """MANDATORY: Verify that FastAPI inference produces exact scores as the frozen ML pipeline."""
    for key, sample in sample_flows.items():
        flow_input = sample["input"]
        expected_score = sample["expected_score"]
        expected_pred = sample["expected_is_anomaly_opA"]

        # 1. Test via MLService directly
        direct_result = loaded_ml_service.predict(flow_input)
        score_diff = abs(direct_result.anomaly_score - expected_score)
        
        # Absolute float difference must be effectively zero (< 1e-9)
        assert score_diff < 1e-9, f"Direct inference score mismatch on {key}: {score_diff}"
        assert direct_result.is_anomaly == expected_pred
        assert direct_result.threshold == pytest.approx(0.521919385, abs=1e-5)

        # 2. Test via FastAPI HTTP endpoint
        response = client.post("/api/v1/detect", json=flow_input)
        assert response.status_code == 200
        api_data = response.json()
        
        api_score = api_data["detection"]["anomaly_score"]
        api_pred = api_data["detection"]["is_anomaly"]
        api_threshold = api_data["detection"]["threshold"]

        # Verify API response matches ground truth
        assert abs(api_score - expected_score) < 1e-5, f"API score mismatch on {key}"
        assert api_pred == expected_pred
        assert api_threshold == pytest.approx(0.521919, abs=1e-5)
