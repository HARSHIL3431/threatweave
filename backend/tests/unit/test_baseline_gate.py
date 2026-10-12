"""P1-14 tests: RAG baseline comparison gate (DI-003).

All fixtures are synthetic dicts in tmp paths; committed baselines are only
read (one integrity test). No model, network, LLM, or index rebuild.
"""
import importlib.util
import json
from pathlib import Path

import pytest

from app.services.rag_evaluation import BASELINE_TOLERANCE, compare_baselines

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _gate_module():
    spec = importlib.util.spec_from_file_location(
        "check_rag_baseline", REPO_ROOT / "scripts" / "check_rag_baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _case(cid, no_match=False, rr=0.0, scores=()):
    return {"case_id": cid, "no_match": no_match,
            "reciprocal_rank": rr, "scores": list(scores)}


def _doc(metrics=None, cases=None, **over):
    doc = {
        "benchmark_version": "rag-benchmark-v1",
        "benchmark_sha256": "abc123",
        "k_values": [1, 3, 5],
        "metrics": {"precision@5": 0.25, "recall@5": 0.6, "mrr@5": 0.5},
        "corpus": {"doc_count": 697, "technique_count": 222,
                   "subtechnique_count": 475, "embedding_model": "m",
                   "embedding_dim": 384, "bundle_sha256": None},
        "coverage": 1.0,
        "errors": [],
        "cases": [_case("RB-1", rr=1.0, scores=(0.7, 0.2)),
                  _case("RB-N", no_match=True, scores=(0.2,))],
    }
    if metrics is not None:
        doc["metrics"] = metrics
    if cases is not None:
        doc["cases"] = cases
    doc.update(over)
    return doc


# 1. Identical current and reference metrics pass.
def test_identical_run_passes():
    gate = compare_baselines(_doc(), _doc())
    assert gate["compatible"] is True
    assert gate["passed"] is True
    assert gate["failures"] == []
    assert gate["incompatibilities"] == []


# 2. A documented regression condition fails and names the metric.
def test_metric_regression_fails():
    current = _doc(metrics={"precision@5": 0.25, "recall@5": 0.55, "mrr@5": 0.5})
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is True
    assert gate["passed"] is False
    assert any("recall@5" in f for f in gate["failures"])


def test_tolerance_boundary_is_inclusive():
    # Half-tolerance dips pass; double-tolerance dips fail. The exact
    # boundary itself is subject to float representation, so the policy is
    # verified strictly inside and outside rather than on the edge.
    inside = {k: (v - BASELINE_TOLERANCE / 2 if k == "recall@5" else v)
              for k, v in _doc()["metrics"].items()}
    assert compare_baselines(_doc(), _doc(metrics=inside))["passed"] is True
    outside = {k: (v - 2 * BASELINE_TOLERANCE if k == "recall@5" else v)
               for k, v in _doc()["metrics"].items()}
    assert compare_baselines(_doc(), _doc(metrics=outside))["passed"] is False


# 3/4. Missing and malformed baselines fail clearly.
def test_missing_baseline_file_fails_clearly(tmp_path):
    gate_mod = _gate_module()
    with pytest.raises(gate_mod.GateInputError):
        gate_mod.load_json_file(tmp_path / "absent.json")


def test_malformed_baseline_fails_clearly(tmp_path):
    gate_mod = _gate_module()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(gate_mod.GateInputError):
        gate_mod.load_json_file(bad)
    not_obj = tmp_path / "list.json"
    not_obj.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(gate_mod.GateInputError):
        gate_mod.load_json_file(not_obj)


# 5. Incompatible versions and case counts are rejected, not compared.
def test_version_mismatch_rejected():
    current = _doc()
    current["benchmark_version"] = "rag-benchmark-v9"
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is False
    assert gate["passed"] is False
    assert any("version" in r for r in gate["incompatibilities"])


def test_case_set_mismatch_rejected():
    current = _doc(cases=[_case("RB-1", rr=1.0, scores=(0.7,))])
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is False
    assert any("case-id" in r for r in gate["incompatibilities"])


def test_fingerprint_mismatch_rejected():
    current = _doc()
    current["corpus"] = dict(current["corpus"], doc_count=700)
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is False
    assert any("doc_count" in r for r in gate["incompatibilities"])


def test_sha_mismatch_rejected():
    current = _doc()
    current["benchmark_sha256"] = "different"
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is False


# 6. Reduced coverage and new errors cannot silently pass.
def test_coverage_drop_fails():
    current = _doc()
    current["coverage"] = 0.5
    gate = compare_baselines(_doc(), current)
    assert gate["passed"] is False
    assert any("coverage" in f for f in gate["failures"])


def test_new_errors_fail_and_name_cases():
    current = _doc()
    current["errors"] = [{"case_id": "RB-1", "error": "boom"}]
    gate = compare_baselines(_doc(), current)
    assert gate["passed"] is False
    assert any("RB-1" in f for f in gate["failures"])


# 7. Missing metrics and invalid numerics are handled safely.
def test_missing_metric_is_incompatible():
    current = _doc(metrics={"precision@5": 0.25})
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is False
    assert gate["passed"] is False


def test_nan_metric_is_incompatible():
    current = _doc(metrics={"precision@5": 0.25, "recall@5": float("nan"),
                            "mrr@5": 0.5})
    gate = compare_baselines(_doc(), current)
    assert gate["compatible"] is False


def test_malformed_documents_do_not_raise():
    gate = compare_baselines({"nope": True}, _doc())
    assert gate["compatible"] is False
    gate2 = compare_baselines("just a string", _doc())
    assert gate2["compatible"] is False


# 8. Per-case relevance loss fails; mere rank shifts are reported.
def test_complete_relevance_loss_fails():
    current = _doc(cases=[_case("RB-1", rr=0.0, scores=(0.1,)),
                          _case("RB-N", no_match=True, scores=(0.2,))])
    gate = compare_baselines(_doc(), current)
    assert gate["passed"] is False
    assert any("RB-1" in f for f in gate["failures"])
    rows = {r["case_id"]: r for r in gate["case_rows"]}
    assert rows["RB-1"]["outcome"] == "relevance-lost"


def test_rank_shift_reported_not_failed():
    current = _doc(cases=[_case("RB-1", rr=0.5, scores=(0.7,)),
                          _case("RB-N", no_match=True, scores=(0.2,))])
    gate = compare_baselines(_doc(), current)
    assert gate["passed"] is True
    rows = {r["case_id"]: r for r in gate["case_rows"]}
    assert rows["RB-1"]["outcome"] == "rank-shifted"


# 9. No-match behavior is preserved in the comparison.
def test_no_match_rows_compared():
    gate = compare_baselines(_doc(), _doc())
    assert gate["passed"] is True
    assert len(gate["no_match_rows"]) == 1
    assert gate["no_match_rows"][0]["case_id"] == "RB-N"


def test_large_no_match_shift_flagged_not_failed():
    current = _doc(cases=[_case("RB-1", rr=1.0, scores=(0.7, 0.2)),
                          _case("RB-N", no_match=True, scores=(0.9,))])
    gate = compare_baselines(_doc(), current)
    assert gate["passed"] is True
    assert gate["no_match_rows"][0]["note"] == "review manually"


# 10. Gate runs never modify reference artifacts.
def test_reference_untouched_by_compare_and_render(tmp_path):
    gate_mod = _gate_module()
    ref_path = tmp_path / "ref.json"
    ref_path.write_text(json.dumps(_doc()), encoding="utf-8")
    before = (ref_path.stat().st_mtime_ns, ref_path.stat().st_size)
    reference = gate_mod.load_json_file(ref_path)
    gate = compare_baselines(reference, _doc())
    assert gate["passed"] is True
    gate_mod.render_report(gate, "rag-benchmark-v1")
    assert (ref_path.stat().st_mtime_ns, ref_path.stat().st_size) == before


def test_json_out_equal_to_baseline_refused(tmp_path):
    gate_mod = _gate_module()
    bench = tmp_path / "rag_benchmark_v9.json"
    bench.write_text("{}", encoding="utf-8")
    with pytest.raises(gate_mod.GateInputError):
        gate_mod.resolve_paths(bench, tmp_path / "rag_baseline_v9.json",
                               tmp_path / "rag_baseline_v9.json")


def test_resolve_paths_default_mapping(tmp_path):
    gate_mod = _gate_module()
    bench = tmp_path / "rag_benchmark_v2.json"
    bench.write_text("{}", encoding="utf-8")
    baseline, out = gate_mod.resolve_paths(bench, None, tmp_path / "cur.json")
    assert baseline == tmp_path / "rag_baseline_v2.json"
    assert out == tmp_path / "cur.json"


# Determinism: repeated comparisons agree exactly.
def test_comparison_deterministic():
    first = compare_baselines(_doc(), _doc())
    second = compare_baselines(_doc(), _doc())
    assert first == second


# Committed baselines are well-formed gate inputs (read-only).
def test_committed_baselines_are_gate_compatible():
    for version in ("v1", "v2"):
        reference = json.loads(
            (REPO_ROOT / "backend" / "tests" / "fixtures" /
             f"rag_baseline_{version}.json").read_text(encoding="utf-8"))
        gate = compare_baselines(reference, reference)
        assert gate["compatible"] is True
        assert gate["passed"] is True
