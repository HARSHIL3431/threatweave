"""P1-8 tests: frozen-detector evaluation math and contract guards.

Pure arithmetic plus frozen-constant verification against the experiment
artifacts (read-only). No training, no retuning, no artifact writes.
"""
import json

import pytest

from app.services.detector_evaluation import (
    E2_EXPERIMENT,
    E2_FEATURE_COUNT,
    OP_A_THRESHOLD,
    OP_B_THRESHOLD,
    accumulate_confusion,
    attack_recall,
    chunked_confusion,
    confusion_at_threshold,
    is_attack,
    normalize_label,
)


def test_frozen_constants_match_artifacts():
    import pickle
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    with open(
        repo_root / "data/processed/experiments/with_port/model.pkl", "rb"
    ) as handle:
        artifact = pickle.load(handle)
    with open(
        repo_root / "data/processed/experiments/with_port/results.json",
        encoding="utf-8",
    ) as handle:
        results = json.load(handle)
    assert artifact["metadata"]["experiment_id"] == E2_EXPERIMENT == "with_port"
    assert artifact["metadata"]["feature_count"] == E2_FEATURE_COUNT == 60
    assert artifact["metadata"]["threshold"] == OP_A_THRESHOLD
    assert results["config"]["frozen_threshold"] == OP_A_THRESHOLD
    assert OP_A_THRESHOLD == pytest.approx(0.5219193851693676)
    assert OP_B_THRESHOLD == pytest.approx(0.4878500998020172)


def test_label_normalization():
    assert normalize_label("  BENIGN  ") == "BENIGN"
    assert normalize_label("DoS Hulk") == "DoS Hulk"
    assert normalize_label("") is None
    assert normalize_label("   ") is None
    assert normalize_label(None) is None
    assert is_attack("BENIGN") is False
    assert is_attack("DoS Hulk") is True


def test_confusion_math():
    metrics = confusion_at_threshold(tp=80, fp=20, tn=70, fn=30)
    assert metrics["precision"] == pytest.approx(0.8)
    assert metrics["recall"] == pytest.approx(80 / 110)
    assert metrics["fpr"] == pytest.approx(20 / 90)
    assert metrics["specificity"] == pytest.approx(70 / 90)
    assert metrics["balanced_accuracy"] == pytest.approx(
        (80 / 110 + 70 / 90) / 2
    )
    assert metrics["f1"] == pytest.approx(2 * 0.8 * (80 / 110) / (0.8 + 80 / 110))


def test_zero_denominators_are_undefined_not_perfect():
    metrics = confusion_at_threshold(tp=0, fp=0, tn=100, fn=0)
    assert metrics["precision"] is None
    assert metrics["recall"] is None
    assert metrics["f1"] is None
    assert metrics["fpr"] == pytest.approx(0.0)
    assert metrics["specificity"] == pytest.approx(1.0)
    assert metrics["balanced_accuracy"] is None

    no_benign = confusion_at_threshold(tp=5, fp=0, tn=0, fn=5)
    assert no_benign["fpr"] is None
    assert no_benign["specificity"] is None
    assert no_benign["balanced_accuracy"] is None
    assert no_benign["recall"] == pytest.approx(0.5)


def test_decision_rule_is_inclusive_threshold():
    counts = accumulate_confusion([0.5, 0.5, 0.4999999], ["X", "BENIGN", "X"], 0.5)
    assert counts == {"tp": 1, "fp": 1, "tn": 0, "fn": 1}


def test_chunked_agrees_with_reference():
    scores = [0.1 * (i % 10) for i in range(1000)]
    labels = ["BENIGN" if i % 3 else "DoS Hulk" for i in range(1000)]
    reference = accumulate_confusion(scores, labels, OP_A_THRESHOLD)
    chunked = chunked_confusion(
        [scores[:333], scores[333:700], scores[700:]],
        [labels[:333], labels[333:700], labels[700:]],
        OP_A_THRESHOLD,
    )
    assert chunked == reference


def test_chunk_length_mismatch_fails_loudly():
    with pytest.raises(ValueError):
        chunked_confusion([[0.1, 0.2]], [["BENIGN"]], OP_A_THRESHOLD)


def test_attack_recall_and_absence():
    scores = [0.9, 0.1, 0.8, 0.2]
    labels = ["DoS Hulk", "DoS Hulk", "BENIGN", "PortScan"]
    rec = attack_recall(scores, labels, "DoS Hulk", 0.5)
    assert rec == {"attack": "DoS Hulk", "samples": 2, "detected": 1,
                   "recall": pytest.approx(0.5)}
    missing = attack_recall(scores, labels, "No Such Attack", 0.5)
    assert missing["samples"] == 0
    assert missing["recall"] is None
