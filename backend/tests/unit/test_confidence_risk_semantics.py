"""P1-10 tests: confidence/risk/severity semantic guards.

Pins the audited meanings so future changes are conscious: risk_score echoes
anomaly_score (no risk model exists), bands mix absolute and relative rules,
and no probability/confidence keys may appear at the detection level.
"""
import pytest

from app.schemas.detection import (
    DetectionDetails,
    DetectionResponse,
    SeverityDetails,
)
from app.services.severity_service import SeverityService


def test_risk_score_echoes_anomaly_score_live(client, sample_flows):
    """risk_score carries no independent risk model: it must equal anomaly_score."""
    for key in ("benign_flow", "anomalous_flow"):
        data = client.post("/api/v1/detect", json=sample_flows[key]["input"]).json()
        assert data["severity"]["risk_score"] == data["detection"]["anomaly_score"]
        assert data["severity"]["calibration_note"] == "INITIAL PLACEHOLDER CALIBRATION"


def test_schema_documents_non_probabilistic_meaning():
    """OpenAPI descriptions must state the placeholder/non-probability semantics."""
    risk_desc = SeverityDetails.model_fields["risk_score"].description or ""
    assert "PLACEHOLDER" in risk_desc
    assert "not a modeled risk probability" in risk_desc
    score_desc = DetectionDetails.model_fields["anomaly_score"].description or ""
    assert "Not a probability" in score_desc


def test_no_probability_keys_at_detection_level():
    """Guard against silently introducing probability/confidence semantics."""
    fields = set(DetectionResponse.model_fields)
    assert not {f for f in fields if "probab" in f or "confiden" in f}, fields
    detection_fields = set(DetectionDetails.model_fields)
    assert detection_fields == {
        "is_anomaly", "anomaly_score", "threshold",
        "experiment_id", "operating_point",
    }


def test_band_edges_are_exact_and_mixed():
    """Absolute critical/high bands vs threshold-relative medium/low/info edges."""
    svc = SeverityService()
    thr = 0.5219193851693676
    assert svc.calculate_severity(0.80, thr).level == "critical"
    assert svc.calculate_severity(0.65, thr).level == "high"
    assert svc.calculate_severity(thr, thr).level == "medium"
    assert svc.calculate_severity(thr * 0.90, thr).level == "low"
    # Absolute bands ignore the operating point: same score, OP-B threshold.
    assert svc.calculate_severity(0.80, 0.4878500998020172).level == "critical"


def test_high_severity_never_contradicts_decision():
    """critical/high/medium bands mathematically imply score >= threshold."""
    svc = SeverityService()
    for thr in (0.5219193851693676, 0.4878500998020172):
        for score in (0.65, 0.80, 0.95):
            assert score >= thr  # absolute bands sit above both frozen thresholds
            assert svc.calculate_severity(score, thr).level in ("high", "critical")


def test_frozen_detector_semantics_untouched(loaded_ml_service, sample_flows):
    """P1-10 changed no detector math: direction, thresholds, decision rule."""
    assert loaded_ml_service.active_threshold == pytest.approx(
        0.5219193851693676, abs=1e-12)
    benign = loaded_ml_service.predict(sample_flows["benign_flow"]["input"])
    anomalous = loaded_ml_service.predict(sample_flows["anomalous_flow"]["input"])
    assert anomalous.anomaly_score > benign.anomaly_score
    assert (anomalous.anomaly_score >= loaded_ml_service.active_threshold) is True
    assert (benign.anomaly_score >= loaded_ml_service.active_threshold) is False
