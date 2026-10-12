"""Deterministic frozen-detector evaluation math (P1-8).

Pure functions over saved anomaly scores and labels. No model loading, no
retraining, no threshold selection: thresholds are frozen constants
verified against the experiment artifacts by test. Zero denominators yield
None ("undefined"), never a fabricated perfect score.
"""

from typing import Any, Dict, List, Optional

# Frozen E2 operating points (must match results.json + sweep record).
OP_A_THRESHOLD = 0.5219193851693676
OP_B_THRESHOLD = 0.4878500998020172
E2_EXPERIMENT = "with_port"
E2_FEATURE_COUNT = 60

BENIGN_LABEL = "BENIGN"


def normalize_label(value: Any) -> Optional[str]:
    """Strip whitespace; empty/missing labels become None (excluded, counted)."""
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def is_attack(label: str) -> bool:
    """Positive class: anything not BENIGN after normalization."""
    return label != BENIGN_LABEL


def confusion_at_threshold(
    tp: int, fp: int, tn: int, fn: int
) -> Dict[str, Optional[float]]:
    """Derive metrics from confusion counts; undefined stays None."""
    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    fpr = fp / (fp + tn) if (fp + tn) > 0 else None
    specificity = tn / (tn + fp) if (tn + fp) > 0 else None
    if recall is None or specificity is None:
        balanced_accuracy = None
    else:
        balanced_accuracy = (recall + specificity) / 2.0
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None if precision is None or recall is None else 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn, "total": total,
        "precision": precision, "recall": recall, "f1": f1,
        "fpr": fpr, "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
    }


def accumulate_confusion(
    scores: List[float], labels: List[str], threshold: float
) -> Dict[str, int]:
    """Count TP/FP/TN/FN in order; decision rule is score >= threshold."""
    tp = fp = tn = fn = 0
    for score, label in zip(scores, labels):
        predicted = score >= threshold
        actual = is_attack(label)
        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and not actual:
            tn += 1
        else:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def chunked_confusion(
    score_chunks: List[List[float]],
    label_chunks: List[List[str]],
    threshold: float,
) -> Dict[str, int]:
    """Order-independent chunked accumulation (sums only)."""
    total = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for scores, labels in zip(score_chunks, label_chunks):
        if len(scores) != len(labels):
            raise ValueError("Score/label chunk length mismatch")
        partial = accumulate_confusion(scores, labels, threshold)
        for key in total:
            total[key] += partial[key]
    return total


def attack_recall(
    scores: List[float], labels: List[str], attack: str, threshold: float
) -> Dict[str, Any]:
    """Recall for one attack label; undefined when the attack is absent."""
    relevant = [s for s, lab in zip(scores, labels) if lab == attack]
    detected = sum(1 for s in relevant if s >= threshold)
    return {
        "attack": attack,
        "samples": len(relevant),
        "detected": detected,
        "recall": (detected / len(relevant)) if relevant else None,
    }
