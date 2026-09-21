from dataclasses import dataclass
from typing import Dict

@dataclass
class SeverityResult:
    """Structured severity classification output."""
    level: str  # "info", "low", "medium", "high", or "critical"
    risk_score: float
    calibration_note: str = "INITIAL PLACEHOLDER CALIBRATION"


class SeverityService:
    """Calculates risk severity for a detected anomaly score.
    
    NOTE: This uses an INITIAL PLACEHOLDER CALIBRATION as specified in project planning.
    These severity tiers are provisional heuristic boundaries and are NOT scientifically
    validated ML operating thresholds. They are designed to be replaced by a calibrated risk model.
    """
    
    PLACEHOLDER_CALIBRATION_NOTE = "INITIAL PLACEHOLDER CALIBRATION"

    def calculate_severity(self, anomaly_score: float, threshold: float) -> SeverityResult:
        """Classify severity level based on anomaly score and active detection threshold.
        
        Tiers:
        - critical: score >= 0.80
        - high:     score >= 0.65
        - medium:   score >= threshold
        - low:      score >= threshold * 0.90
        - info:     score < threshold * 0.90
        """
        score = float(anomaly_score)
        thr = float(threshold)
        
        if score >= 0.80:
            level = "critical"
        elif score >= 0.65:
            level = "high"
        elif score >= thr:
            level = "medium"
        elif score >= thr * 0.90:
            level = "low"
        else:
            level = "info"

        return SeverityResult(
            level=level,
            risk_score=round(score, 6),
            calibration_note=self.PLACEHOLDER_CALIBRATION_NOTE,
        )
