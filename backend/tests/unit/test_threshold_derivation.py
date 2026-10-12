"""P1-16 tests: threshold re-derivation helpers (DI-012 procedure plumbing).

Offline and deterministic. All labeled inputs below are inline synthetic
fixtures for plumbing only — they carry no authority and demonstrate no
threshold recommendation. Production retrieval is never touched here.
"""
import pytest

from app.services.rag_evaluation import (
    ThresholdError,
    evaluate_candidate_threshold,
    validate_threshold_split,
)


def _retrieved(pairs):
    return [{"technique_id": tid, "score": s} for tid, s in pairs]


def _labels():
    return [
        {"case_id": "S-REL-1", "status": "relevant", "relevant_ids": ["T1003"]},
        {"case_id": "S-REL-2", "status": "relevant", "relevant_ids": ["T1046"]},
        {"case_id": "S-NM-1", "status": "no_match", "relevant_ids": []},
        {"case_id": "S-UN-1", "status": "unresolved", "relevant_ids": []},
    ]


def _scores():
    return {
        # Relevant hit above the floor -> retained.
        "S-REL-1": _retrieved([("T1003.001", 0.70), ("T9999", 0.80)]),
        # Relevant hit exists but below the floor -> falsely suppressed.
        "S-REL-2": _retrieved([("T1046", 0.30), ("T9999", 0.90)]),
        # Every score below the floor -> suppressed.
        "S-NM-1": _retrieved([("T9999", 0.20), ("T9998", 0.10)]),
        # Unresolved: never enters primary rates whatever its scores.
        "S-UN-1": _retrieved([("T1003", 0.99)]),
    }


def test_candidate_rates_and_outcomes():
    report = evaluate_candidate_threshold(_labels(), _scores(), 0.5)
    assert report["threshold"] == 0.5
    assert (report["n_relevant"], report["n_no_match"],
            report["n_unresolved"], report["n_errors"]) == (2, 1, 1, 0)
    assert report["retained_relevant_rate"] == pytest.approx(0.5)
    assert report["false_suppression_rate"] == pytest.approx(0.5)
    assert report["no_match_suppression_rate"] == pytest.approx(1.0)
    assert report["unresolved_case_ids"] == ["S-UN-1"]
    assert report["unresolved_max_scores"] == [
        {"case_id": "S-UN-1", "max_score": 0.99}]
    by_id = {r["case_id"]: r for r in report["per_case"]}
    assert by_id["S-REL-1"]["outcome"] == "retained"
    assert by_id["S-REL-1"]["max_relevant_score"] == pytest.approx(0.70)
    assert by_id["S-REL-2"]["outcome"] == "suppressed"
    assert by_id["S-NM-1"]["outcome"] == "suppressed"
    assert by_id["S-UN-1"]["outcome"] == "excluded-unresolved"


def test_boundary_score_equal_to_floor_is_kept():
    labels = [{"case_id": "B", "status": "relevant", "relevant_ids": ["T1003"]}]
    report = evaluate_candidate_threshold(
        labels, {"B": _retrieved([("T1003", 0.5)])}, 0.5)
    assert report["retained_relevant_rate"] == pytest.approx(1.0)


def test_empty_result_sets_have_explicit_denominator_rules():
    labels = [
        {"case_id": "E-R", "status": "relevant", "relevant_ids": ["T1003"]},
        {"case_id": "E-N", "status": "no_match", "relevant_ids": []},
    ]
    report = evaluate_candidate_threshold(
        labels, {"E-R": [], "E-N": []}, 0.5)
    by_id = {r["case_id"]: r for r in report["per_case"]}
    # Empty retrieval keeps nothing: a relevant case is suppressed ...
    assert by_id["E-R"]["outcome"] == "suppressed"
    assert by_id["E-R"]["max_score"] is None
    # ... while a no-match case is vacuously suppressed.
    assert by_id["E-N"]["outcome"] == "suppressed"
    assert report["false_suppression_rate"] == pytest.approx(1.0)
    assert report["no_match_suppression_rate"] == pytest.approx(1.0)


def test_missing_and_malformed_inputs_become_errors_not_drops():
    labels = _labels()
    scores = _scores()
    del scores["S-REL-1"]
    scores["S-NM-1"] = [{"technique_id": "T9999", "score": "high"}]
    report = evaluate_candidate_threshold(labels, scores, 0.5)
    assert report["n_errors"] == 2
    assert {e["case_id"] for e in report["errors"]} == {"S-REL-1", "S-NM-1"}
    # Error cases leave every denominator; only decided, scored cases count.
    assert report["n_relevant"] == 1
    assert report["n_no_match"] == 0
    assert report["no_match_suppression_rate"] is None


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), True, None])
def test_non_finite_scores_are_errors(bad_score):
    labels = [{"case_id": "M", "status": "no_match", "relevant_ids": []}]
    report = evaluate_candidate_threshold(
        labels, {"M": [{"technique_id": "T9999", "score": bad_score}]}, 0.5)
    assert report["n_errors"] == 1
    assert report["n_no_match"] == 0


def test_label_validation_rejects_ambiguous_or_bad_records():
    base = {"case_id": "X", "status": "relevant", "relevant_ids": ["T1003"]}
    retrieved = {"X": _retrieved([("T1003", 0.6)])}
    # Relevant with no IDs, no-match with IDs, bad status, bad ID shape.
    for bad in [
        {"case_id": "X", "status": "relevant", "relevant_ids": []},
        {"case_id": "X", "status": "no_match", "relevant_ids": ["T1003"]},
        {"case_id": "X", "status": "maybe", "relevant_ids": []},
        {"case_id": "X", "status": "relevant", "relevant_ids": ["nope"]},
    ]:
        with pytest.raises(ThresholdError):
            evaluate_candidate_threshold([bad], retrieved, 0.5)
    with pytest.raises(ThresholdError):
        evaluate_candidate_threshold(
            [dict(base), dict(base)], retrieved, 0.5)  # duplicate case
    for bad_floor in [float("nan"), "0.5", True, None]:
        with pytest.raises(ThresholdError):
            evaluate_candidate_threshold([base], retrieved, bad_floor)
    with pytest.raises(ThresholdError):
        evaluate_candidate_threshold([], retrieved, 0.5)


def test_split_accepts_disjoint_sets():
    split = validate_threshold_split(["RB-001", "RB-002"], ["RB-003"])
    assert split == {"n_dev": 2, "n_heldout": 1,
                     "dev_ids": ["RB-001", "RB-002"], "heldout_ids": ["RB-003"]}


def test_split_rejects_leakage_including_shared_version_scenarios():
    # v1 and v2 share 17 identical payloads under stable case IDs: a split
    # that puts RB-001 in dev and RB-001 in held-out leaks the scenario even
    # though the version-qualified records differ. Callers normalize to the
    # scenario key first, so the validator sees the collision.
    dev = ["RB-001", "RB-002"]          # e.g. normalized from v1 records
    heldout = ["RB-001", "RB-016"]      # ... and v2 records
    with pytest.raises(ThresholdError, match="leak"):
        validate_threshold_split(dev, heldout)


def test_split_rejects_empty_duplicate_and_malformed_sets():
    with pytest.raises(ThresholdError):
        validate_threshold_split([], ["RB-001"])
    with pytest.raises(ThresholdError):
        validate_threshold_split(["RB-001"], [])
    with pytest.raises(ThresholdError):
        validate_threshold_split(["RB-001", "RB-001"], ["RB-002"])
    with pytest.raises(ThresholdError):
        validate_threshold_split(["RB-001", ""], ["RB-002"])
    with pytest.raises(ThresholdError):
        validate_threshold_split("RB-001", ["RB-002"])


def test_helpers_are_deterministic():
    first = evaluate_candidate_threshold(_labels(), _scores(), 0.5)
    second = evaluate_candidate_threshold(_labels(), _scores(), 0.5)
    assert first == second
