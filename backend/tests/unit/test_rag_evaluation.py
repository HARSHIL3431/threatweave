"""P1-2 tests: evaluation metric arithmetic, policies, and determinism.

Metric tests use hand-computable synthetic fixtures. Pipeline-shape tests use
FakeEmbedder stores (no model download). No network, no rebuild, no LLM.
"""
import json

import pytest

from app.services.rag_evaluation import (
    BENCHMARK_VERSION,
    BenchmarkError,
    apply_score_floor,
    apply_score_margin,
    evaluate_case,
    evaluate_policy,
    is_relevant,
    load_benchmark_file,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    run_benchmark,
    validate_benchmark,
)


def _case(case_id="RB-X", expected=("T1003",), no_match=False):
    return {
        "case_id": case_id,
        "query": "synthetic query",
        "expected_ids": list(expected),
        "no_match": no_match,
        "label_provenance": "synthetic",
        "rationale": "test rationale",
        "ambiguity": "none",
    }


def _hits(*ids, score=0.9):
    return [{"technique_id": tid, "score": score - 0.01 * i} for i, tid in enumerate(ids)]


# 1. Correct metric calculations on hand-computable examples.
def test_hand_computable_metrics():
    retrieved = ["T1003", "T1110", "T1059", "T1046", "T1078"]
    expected = ["T1003", "T1046"]
    assert precision_at_k(retrieved, expected, 5) == pytest.approx(0.4)
    assert precision_at_k(retrieved, expected, 2) == pytest.approx(0.5)
    assert recall_at_k(retrieved, expected, 5) == pytest.approx(1.0)
    assert recall_at_k(retrieved, expected, 2) == pytest.approx(0.5)
    assert reciprocal_rank(retrieved, expected, 5) == pytest.approx(1.0)


# 2/3/4. Rank-one hit, later-rank hit, and complete miss.
def test_rank_positions():
    assert reciprocal_rank(["T1003", "T1110"], ["T1003"], 5) == pytest.approx(1.0)
    assert reciprocal_rank(["T1110", "T1059", "T1003"], ["T1003"], 5) == pytest.approx(1 / 3)
    assert reciprocal_rank(["T1110", "T1059"], ["T1003"], 5) == pytest.approx(0.0)
    # Truncation: hit at rank 3 is invisible at K=2.
    assert reciprocal_rank(["T1110", "T1059", "T1003"], ["T1003"], 2) == pytest.approx(0.0)


# 6. Empty result lists and fewer-than-K results.
def test_empty_and_short_results():
    assert precision_at_k([], ["T1003"], 5) == pytest.approx(0.0)
    assert recall_at_k([], ["T1003"], 5) == pytest.approx(0.0)
    assert reciprocal_rank([], ["T1003"], 5) == pytest.approx(0.0)
    # Denominator is min(K, returned): 1/2, not 1/5.
    assert precision_at_k(["T1003", "T1110"], ["T1003"], 5) == pytest.approx(0.5)
    assert recall_at_k(["T1003"], ["T1003", "T1046"], 5) == pytest.approx(0.5)


# 7. Duplicate result handling (defensive; pipeline cannot emit these).
def test_duplicates_deduped():
    retrieved = ["T1110", "T1003", "T1003", "T1046"]
    assert precision_at_k(retrieved, ["T1003"], 5) == pytest.approx(1 / 3)
    assert reciprocal_rank(retrieved, ["T1003"], 5) == pytest.approx(1 / 2)


# 8. Multiple acceptable expected technique IDs.
def test_multiple_acceptable_ids():
    retrieved = ["T1110", "T1595"]
    assert recall_at_k(retrieved, ["T1595", "T1046"], 5) == pytest.approx(0.5)
    assert precision_at_k(retrieved, ["T1595", "T1046"], 5) == pytest.approx(0.5)


# 9. Parent/sub-technique mapping policy.
def test_parent_subtechnique_policy():
    assert is_relevant("T1003.001", ["T1003"]) is True  # sub satisfies parent
    assert is_relevant("T1003", ["T1003"]) is True  # exact
    assert is_relevant("T1003", ["T1003.001"]) is False  # parent lacks specificity
    assert is_relevant("T1110", ["T1003"]) is False
    assert recall_at_k(["T1003.001"], ["T1003"], 5) == pytest.approx(1.0)


# 5/6. No-match evaluation records scores without polluting aggregates.
def test_no_match_case_evaluation():
    case = _case("RB-N", expected=(), no_match=True)
    result = evaluate_case(case, _hits("T1003", "T1110"), [1, 3, 5])
    assert result.per_k == {}
    assert result.reciprocal_rank == pytest.approx(0.0)
    report = run_benchmark([case], lambda q, k: _hits("T1003", "T1110")[:k], [5])
    assert report["n_no_match"] == 1
    assert report["n_evaluable"] == 0
    assert report["aggregates"]["precision@5"] == pytest.approx(0.0)
    assert report["no_match"][0]["n_returned"] == 2
    assert report["no_match"][0]["max_score"] == pytest.approx(0.9)


# 10. Invalid benchmark labels and malformed records fail loudly.
@pytest.mark.parametrize("mutate", [
    lambda d: d["cases"].__setitem__(0, "not-a-dict"),
    lambda d: d["cases"][0].update({"expected_ids": ["NOT-A-TECHNIQUE"]}),
    lambda d: d["cases"][0].update({"no_match": True, "expected_ids": ["T1003"]}),
    lambda d: d["cases"][0].update({"expected_ids": []}),
    lambda d: d["cases"][0].update({"query": "   "}),
    lambda d: d["cases"][0].update({"label_provenance": "expert-validated"}),
    lambda d: d["cases"][0].update({"rationale": ""}),
    lambda d: d["cases"].append(dict(d["cases"][0])),
    lambda d: d.update({"version": "something-else"}),
    lambda d: d.update({"cases": []}),
])
def test_invalid_benchmark_rejected(mutate):
    data = {"version": BENCHMARK_VERSION, "cases": [_case()]}
    mutate(data)
    with pytest.raises(BenchmarkError):
        validate_benchmark(data)


# 11. Retrieval failures are captured, never fabricated or dropped.
def test_retrieval_error_captured():
    def boom(query, k):
        raise RuntimeError("index gone")

    report = run_benchmark([_case(), _case("RB-Y")], boom, [5])
    assert report["n_errors"] == 2
    assert report["coverage"] == pytest.approx(0.0)
    assert report["aggregates"]["precision@5"] == pytest.approx(0.0)
    assert [e["case_id"] for e in report["errors"]] == ["RB-X", "RB-Y"]


def test_partial_errors_keep_good_cases():
    calls = {"n": 0}

    def flaky(query, k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return _hits("T1003")

    report = run_benchmark([_case("RB-A"), _case("RB-B")], flaky, [5])
    assert report["coverage"] == pytest.approx(0.5)
    assert report["n_evaluable"] == 1
    assert report["aggregates"]["recall@5"] == pytest.approx(1.0)


# 13. Repeated evaluation is byte-identical in metrics and ordering.
def test_deterministic_rerun(make_store, fake_embedder):
    from app.services.rag_service import RagService, clear_rag_cache
    from app.services.vector_store import VectorStore

    docs = [
        {"text": f"Technique Doc {i} T-PAD-{i}",
         "meta": {"technique_id": f"T-PAD-{i}", "technique_name": f"Pad {i}",
                  "type": "technique", "tactics": [], "description": f"pad {i}",
                  "detection": None, "mitigations": [], "data_sources": [],
                  "platforms": []}}
        for i in range(3)
    ]
    index_path, metadata_path = make_store(docs)
    rag = RagService(enabled=True, index_path=index_path, metadata_path=metadata_path,
                     embedder=fake_embedder, top_k=5)
    try:
        def retrieve(query, k):
            return [
                {"technique_id": r.technique_id, "score": r.score}
                for r in rag.query(query, top_k=k)
            ]

        cases = [_case("RB-A", expected=("T-PAD-0",)), _case("RB-B", expected=("T-PAD-1",))]
        first = run_benchmark(cases, retrieve, [1, 3, 5])
        second = run_benchmark(cases, retrieve, [1, 3, 5])
        assert first == second
        assert [c["case_id"] for c in first["cases"]] == ["RB-A", "RB-B"]
    finally:
        clear_rag_cache()


# 12. Unknown/stale provenance represented accurately (passthrough shape).
def test_provenance_block_shape():
    freshness = {"built_at": None, "knowledge_age_status": "unknown", "is_stale": False}
    assert freshness["knowledge_age_status"] == "unknown"
    assert freshness["is_stale"] is False


# 14. Evaluation path performs no downloads, rebuilds, or LLM calls.
def test_no_side_effects(make_store, fake_embedder, tmp_path, monkeypatch):
    from app.services.rag_service import RagService, clear_rag_cache

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    index_path, metadata_path = make_store([
        {"text": "Technique Solo (T-SOLO)",
         "meta": {"technique_id": "T-SOLO", "technique_name": "Solo",
                  "type": "technique", "tactics": [], "description": "solo",
                  "detection": None, "mitigations": [], "data_sources": [],
                  "platforms": []}},
    ])
    calls = {"embed": 0}
    orig_embed = fake_embedder.embed

    def counting_embed(texts, batch_size=32):
        calls["embed"] += 1
        return orig_embed(texts, batch_size=batch_size)

    fake_embedder.embed = counting_embed
    rag = RagService(enabled=True, index_path=index_path, metadata_path=metadata_path,
                     embedder=fake_embedder, top_k=5)
    before_index = index_path.stat().st_mtime_ns
    before_meta = metadata_path.stat().st_mtime_ns
    try:
        report = run_benchmark(
            [_case("RB-A", expected=("T-SOLO",))],
            lambda q, k: [
                {"technique_id": r.technique_id, "score": r.score}
                for r in rag.query(q, top_k=k)
            ],
            [5],
        )
        assert report["coverage"] == pytest.approx(1.0)
        assert calls["embed"] == 1  # one query embedded; no rebuild re-embedding
        assert index_path.stat().st_mtime_ns == before_index
        assert metadata_path.stat().st_mtime_ns == before_meta
    finally:
        clear_rag_cache()


def test_shipped_benchmark_validates():
    from pathlib import Path

    dataset = load_benchmark_file(
        Path(__file__).parent.parent / "fixtures" / "rag_benchmark_v1.json"
    )
    assert dataset["version"] == BENCHMARK_VERSION
    assert len(dataset["cases"]) == 17
    assert sum(1 for c in dataset["cases"] if c["no_match"]) == 2
    assert len(dataset["sha256"]) == 64


# ---------------------------------------------------------------------------
# P1-4: no-match policy helpers and v2 preservation.
# ---------------------------------------------------------------------------
def _scored(*pairs):
    return [{"technique_id": tid, "score": score} for tid, score in pairs]


def test_score_floor_keeps_order_and_threshold():
    retrieved = _scored(("T-A", 0.8), ("T-B", 0.5), ("T-C", 0.2))
    assert [r["technique_id"] for r in apply_score_floor(retrieved, 0.5)] == ["T-A", "T-B"]
    assert apply_score_floor(retrieved, 0.9) == []
    assert apply_score_floor([], 0.1) == []


def test_score_margin_relative_to_top():
    retrieved = _scored(("T-A", 0.8), ("T-B", 0.75), ("T-C", 0.2))
    assert [r["technique_id"] for r in apply_score_margin(retrieved, 0.1)] == ["T-A", "T-B"]
    assert [r["technique_id"] for r in apply_score_margin(retrieved, 0.0)] == ["T-A"]
    assert apply_score_margin([], 0.5) == []


def test_policy_tradeoff_hand_computed():
    cases = [
        {"case_id": "R1", "no_match": False, "expected_ids": ["T-A"]},
        {"case_id": "R2", "no_match": False, "expected_ids": ["T-B"]},
        {"case_id": "N1", "no_match": True, "expected_ids": []},
    ]
    recorded = {
        "R1": _scored(("T-A", 0.9), ("T-X", 0.1)),
        "R2": _scored(("T-Y", 0.8)),
        "N1": _scored(("T-Z", 0.4)),
    }
    report = evaluate_policy(cases, recorded, lambda r: apply_score_floor(r, 0.5))
    assert report["kept_relevant_rate"] == pytest.approx(0.5)
    assert report["mean_kept_evaluable"] == pytest.approx(1.0)
    assert report["no_match_suppression_rate"] == pytest.approx(1.0)
    assert report["n_errors"] == 0


def test_policy_missing_case_is_error_not_dropped():
    cases = [{"case_id": "R1", "no_match": False, "expected_ids": ["T-A"]}]
    report = evaluate_policy(cases, {}, lambda r: r)
    assert report["n_errors"] == 1
    assert report["errors"][0]["case_id"] == "R1"


def test_benchmark_v2_preserves_v1_cases():
    from pathlib import Path

    fixtures = Path(__file__).parent.parent / "fixtures"
    v1 = json.loads((fixtures / "rag_benchmark_v1.json").read_text(encoding="utf-8"))
    dataset = load_benchmark_file(fixtures / "rag_benchmark_v2.json")
    assert dataset["version"] == "rag-benchmark-v2"
    assert len(dataset["cases"]) == 25
    for old, new in zip(v1["cases"], dataset["cases"][:17]):
        assert old == new
    new_ids = [c["case_id"] for c in dataset["cases"][17:]]
    assert new_ids == ["RB-016", "RB-017", "RB-N03", "RB-N04",
                       "RB-N05", "RB-N06", "RB-N07", "RB-N08"]
    assert sum(1 for c in dataset["cases"] if c["no_match"]) == 9
