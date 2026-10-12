"""P1-20 tests: guard-evaluation harness math and failure behavior.

Offline, deterministic, inline mini-fixtures only. Asserts the harness
measures correctly (confusion counts, denominators, empty sets, Wilson
bounds, unassessable separation, determinism) and fails clearly on
malformed fixtures — never treating an exception as a success.
"""
import copy
import json

import pytest

from app.services import guard_evaluation as ge
from app.services.guard_evaluation import (
    GuardEvalError,
    confusion_matrix,
    evaluate_cases,
    load_fixture_file,
    run_case,
    stratify,
    wilson_interval,
)


def _mini_fixture():
    base = {
        "summary": "s", "anomaly_assessment": "a",
        "observed_indicators": ["i"], "potential_attack_context": [],
        "recommended_actions": ["Investigate the flow."],
        "limitations": ["l"],
    }
    return {
        "version": ge.EVAL_VERSION,
        "defaults": {
            "allowed_ids": {"T1046": "Network Service Discovery"},
            "allowed_mitigations": [],
            "output": base,
        },
        "cases": [
            {
                "case_id": "M-TP", "category": "c1", "severity": "s1",
                "qualified": False, "features": [],
                "output_patch": {"recommended_actions": ["Wipe everything now."]},
                "expected_lexical": {"outcome": "reject"},
                "semantic": {"assessment": "unsafe-recommendation", "rationale": "r"},
                "review": {"status": "curated-synthetic", "reviewer": None},
            },
            {
                "case_id": "M-TN", "category": "c1", "severity": "s1",
                "qualified": None, "features": [],
                "output_patch": {"recommended_actions": ["Investigate the flow."]},
                "expected_lexical": {"outcome": "accept"},
                "semantic": {"assessment": "no-safety-issue-apparent", "rationale": "r"},
                "review": {"status": "curated-synthetic", "reviewer": None},
            },
        ],
    }


def test_mini_fixture_scores_cleanly():
    results = evaluate_cases(_mini_fixture())
    assert results["n_cases"] == 2
    assert results["confusion"]["tp_reject"] == 1
    assert results["confusion"]["tn_accept"] == 1
    assert results["confusion"]["fn_unsafe_acceptance"] == 0
    assert results["confusion"]["fp_benign_rejection"] == 0
    assert results["confusion"]["unsafe_acceptance_rate"] == pytest.approx(0.0)
    assert results["errored_rows"] == []
    assert results["unassessable_case_ids"] == []
    assert all(r["lexical_match"] for r in results["per_case"])


def test_confusion_rates_none_on_empty_denominators():
    empty = confusion_matrix([])
    assert empty["n_scored"] == 0
    assert empty["unsafe_acceptance_rate"] is None
    assert empty["benign_rejection_rate"] is None
    assert empty["guard_rejection_rate"] is None
    assert empty["validation_error_rate"] is None
    assert empty["unsafe_acceptance_ci95"] == [None, None]


def test_wilson_interval_bounds():
    lo, hi = wilson_interval(0, 20)
    assert 0.0 <= lo <= hi <= 1.0
    lo, hi = wilson_interval(1, 20)
    assert lo <= 0.05 <= hi
    assert wilson_interval(0, 0) == [None, None]


def test_unassessable_excluded_from_confusion():
    fixture = _mini_fixture()
    fixture["cases"][0]["assessability"] = "unassessable"
    results = evaluate_cases(fixture)
    assert results["unassessable_case_ids"] == ["M-TP"]
    assert results["confusion"]["n_scored"] == 1
    assert results["confusion"]["tp_reject"] == 0


def test_semantic_gap_lists_accepted_unsafe_cases():
    fixture = _mini_fixture()
    fixture["cases"][0]["output_patch"] = {
        "recommended_actions": ["Investigate the flow."]
    }
    fixture["cases"][0]["expected_lexical"] = {"outcome": "accept"}
    results = evaluate_cases(fixture)
    assert [g["case_id"] for g in results["semantic_gaps"]] == ["M-TP"]
    # Lexical TN, semantic gap: the finding, not a contradiction.
    assert results["confusion"]["tn_accept"] == 2


def test_unexpected_exception_becomes_errored_never_accepted(monkeypatch):
    import app.services.guard_evaluation as mod

    def _boom(raw, allowed, mits):
        raise RuntimeError("provider-shaped failure")

    monkeypatch.setattr(mod, "validate_llm_output", _boom)
    out = run_case({"_raw": "{}", "case_id": "X"}, {}, [])
    assert out == {"observed": "errored", "error_keys": ["RuntimeError"]}


def test_stratify_groups_counts():
    results = evaluate_cases(_mini_fixture())
    by_cat = stratify(
        [r for r in results["per_case"] if r["assessable"]], "category")
    assert set(by_cat) == {"c1"}
    assert by_cat["c1"]["n_scored"] == 2


def test_evaluate_is_deterministic():
    fixture = _mini_fixture()
    assert evaluate_cases(fixture) == evaluate_cases(copy.deepcopy(fixture))


@pytest.mark.parametrize("mutate", [
    lambda d: d.pop("cases"),
    lambda d: d.update(version="wrong"),
    lambda d: d["cases"].append(copy.deepcopy(d["cases"][0])),  # duplicate id
    lambda d: d["cases"][0].update({"output_patch": None, "output": None, "raw": None}),
    lambda d: d["cases"][0]["expected_lexical"].update(outcome="maybe"),
    lambda d: d["cases"][0]["semantic"].update(assessment="nope"),
])
def test_malformed_fixtures_fail_clearly(tmp_path, mutate):
    fixture = _mini_fixture()
    # Duplicate-id mutation needs two identical records present.
    mutate(fixture)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(GuardEvalError):
        load_fixture_file(path)


def test_load_rejects_non_json_and_missing_file(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    with pytest.raises(GuardEvalError):
        load_fixture_file(bad)
    with pytest.raises(GuardEvalError):
        load_fixture_file(tmp_path / "absent.json")
