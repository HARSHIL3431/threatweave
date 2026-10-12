"""P1-6 tests: label-review queue integrity and baseline source integrity.

Offline and deterministic. Fixtures are read, never modified. No network,
no model loading beyond the tiny FakeEmbedder stores used elsewhere (none
needed here except metric recomputation, which is pure arithmetic).
"""
import copy
import json
from pathlib import Path

import pytest

from app.services.rag_evaluation import (
    ReviewError,
    evaluate_case,
    run_benchmark,
    validate_benchmark,
    validate_review_queue,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _benchmark_cases(version):
    data = _load("rag_benchmark_v1.json" if version == "rag-benchmark-v1"
                 else "rag_benchmark_v2.json")
    assert validate_benchmark(data)["version"] == version
    return {(version, c["case_id"]): c for c in data["cases"]}


def _all_benchmark_cases():
    cases = {}
    cases.update(_benchmark_cases("rag-benchmark-v1"))
    cases.update(_benchmark_cases("rag-benchmark-v2"))
    return cases


def _review():
    return _load("rag_label_review_v1.json")


# Every benchmark case is represented in the review queue.
def test_review_queue_covers_all_cases():
    summary = validate_review_queue(_review(), _all_benchmark_cases())
    assert summary == {
        "n_records": 42,
        "n_expected": 42,
        "by_status": {"pending": 42},
        "n_pending": 42,
        "n_decided": 0,
        # RB-014 suggestion in both versions + RB-016 schema suggestion (v2 only).
        "n_proposed_changes": 3,
    }


# Case IDs and versions resolve; originals match sources byte-for-byte.
def test_review_originals_match_sources():
    review = _review()
    cases = _all_benchmark_cases()
    assert len(review["records"]) == 42
    for rec in review["records"]:
        source = cases[(rec["benchmark_version"], rec["case_id"])]
        assert rec["original"]["query"] == source["query"]
        assert rec["original"]["expected_ids"] == source["expected_ids"]
        assert rec["original"]["no_match"] == source["no_match"]
        assert rec["synthetic"] is True
        assert rec["human_review_recorded"] is False


# Duplicate review entries are rejected.
def test_duplicate_review_entries_rejected():
    review = _review()
    duped = copy.deepcopy(review)
    duped["records"].append(copy.deepcopy(review["records"][0]))
    with pytest.raises(ReviewError):
        validate_review_queue(duped, _all_benchmark_cases())


# Unknown version/case and coverage gaps are rejected.
def test_unknown_and_missing_cases_rejected():
    review = _review()
    bad = copy.deepcopy(review)
    bad["records"][0]["case_id"] = "RB-DOES-NOT-EXIST"
    with pytest.raises(ReviewError):
        validate_review_queue(bad, _all_benchmark_cases())

    short = copy.deepcopy(review)
    short["records"] = short["records"][:-1]
    with pytest.raises(ReviewError):
        validate_review_queue(short, _all_benchmark_cases())


# Invalid statuses and malformed proposals are rejected.
def test_invalid_status_and_proposal_rejected():
    review = _review()
    bad = copy.deepcopy(review)
    bad["records"][3]["status"] = "approved"
    with pytest.raises(ReviewError):
        validate_review_queue(bad, _all_benchmark_cases())

    bad2 = copy.deepcopy(review)
    bad2["records"][3]["automated_proposal"]["outcome"] = "maybe"
    with pytest.raises(ReviewError):
        validate_review_queue(bad2, _all_benchmark_cases())

    bad3 = copy.deepcopy(review)
    bad3["records"][3]["automated_proposal"]["analyzer"] = "expert-panel"
    with pytest.raises(ReviewError):
        validate_review_queue(bad3, _all_benchmark_cases())


# Automated proposals cannot masquerade as completed human reviews.
def test_automation_cannot_pose_as_human_review():
    review = _review()
    sneaky = copy.deepcopy(review)
    sneaky["records"][0]["status"] = "decided"  # reviewer block still blank
    with pytest.raises(ReviewError):
        validate_review_queue(sneaky, _all_benchmark_cases())

    forged = copy.deepcopy(review)
    forged["records"][0]["reviewer"]["decision"] = "accept"  # no identity/date
    with pytest.raises(ReviewError):
        validate_review_queue(forged, _all_benchmark_cases())


# Missing reviewer metadata never becomes fabricated sign-off; approval needs all four.
def test_approval_requires_full_reviewer_metadata():
    review = _review()
    for missing in ("identity", "date", "decision", "rationale"):
        bad = copy.deepcopy(review)
        rec = bad["records"][1]
        rec["status"] = "decided"
        rec["reviewer"] = {"identity": "analyst-x", "date": "2026-10-11",
                           "decision": "accept", "rationale": "verified"}
        rec["reviewer"][missing] = None
        with pytest.raises(ReviewError):
            validate_review_queue(bad, _all_benchmark_cases())

    approved = copy.deepcopy(review)
    rec = approved["records"][1]
    rec["status"] = "decided"
    rec["reviewer"] = {"identity": "analyst-x", "date": "2026-10-11",
                       "decision": "accept", "rationale": "verified against corpus"}
    summary = validate_review_queue(approved, _all_benchmark_cases())
    assert summary["n_decided"] == 1
    assert summary["n_pending"] == 41


# No-match and technique-label types remain unambiguous in review records.
def test_review_label_types_unambiguous():
    for rec in _review()["records"]:
        original = rec["original"]
        assert isinstance(original["no_match"], bool)
        if original["no_match"]:
            assert original["expected_ids"] == []
        else:
            assert len(original["expected_ids"]) >= 1


# Baseline artifacts are faithful: metrics recompute from recorded results.
@pytest.mark.parametrize("version,k_values", [
    ("rag-benchmark-v1", [1, 3, 5]),
    ("rag-benchmark-v2", [1, 3, 5]),
])
def test_baseline_metrics_recompute(version, k_values):
    bench_file = "rag_benchmark_v1.json" if version == "rag-benchmark-v1" \
        else "rag_benchmark_v2.json"
    base_file = "rag_baseline_v1.json" if version == "rag-benchmark-v1" \
        else "rag_baseline_v2.json"
    bench = {c["case_id"]: c for c in _load(bench_file)["cases"]}
    base = _load(base_file)
    assert base["benchmark_version"] == version
    # Baseline case IDs match the benchmark exactly (no added/dropped cases).
    assert [c["case_id"] for c in base["cases"]] == [c["case_id"] for c in _load(bench_file)["cases"]]

    # Recompute per-case metrics from the RECORDED retrieved lists.
    # Retrieval never runs here; recorded data only (no model, no network).
    for record in base["cases"]:
        case = bench[record["case_id"]]
        retrieved = [{"technique_id": t, "score": s}
                     for t, s in zip(record["retrieved_ids"], record["scores"])]
        result = evaluate_case(case, retrieved, k_values)
        if case["no_match"]:
            assert result.per_k == {}
            continue
        for k in k_values:
            for metric in ("precision", "recall"):
                assert result.per_k[k][metric] == pytest.approx(
                    record["per_k"][str(k)][metric], abs=1e-3), \
                    (version, record["case_id"], k, metric)


# Existing evaluator semantics unchanged (smoke: shipped baselines validate).
def test_baselines_reference_supported_benchmarks():
    for name in ("rag_baseline_v1.json", "rag_baseline_v2.json"):
        base = _load(name)
        assert base["benchmark_version"] in ("rag-benchmark-v1", "rag-benchmark-v2")
        assert base["coverage"] == 1.0
        assert base["errors"] == []
