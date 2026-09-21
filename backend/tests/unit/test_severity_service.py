import pytest
from app.services.severity_service import SeverityService


def test_severity_tiers():
    """Verify classification across all provisional risk tiers."""
    svc = SeverityService()
    thr = 0.521919

    # Critical: score >= 0.80
    res_crit = svc.calculate_severity(0.85, thr)
    assert res_crit.level == "critical"
    assert res_crit.risk_score == 0.85

    # High: score >= 0.65
    res_high = svc.calculate_severity(0.70, thr)
    assert res_high.level == "high"
    assert res_high.risk_score == 0.70

    # Medium: score >= threshold
    res_med = svc.calculate_severity(0.55, thr)
    assert res_med.level == "medium"
    assert res_med.risk_score == 0.55

    # Low: score >= threshold * 0.90
    res_low = svc.calculate_severity(thr * 0.95, thr)
    assert res_low.level == "low"

    # Info: score < threshold * 0.90
    res_info = svc.calculate_severity(thr * 0.80, thr)
    assert res_info.level == "info"


def test_severity_placeholder_note():
    """Verify calibration note is prominently displayed and disclaimed."""
    svc = SeverityService()
    res = svc.calculate_severity(0.75, 0.52)
    assert res.calibration_note == "INITIAL PLACEHOLDER CALIBRATION"
