#!/usr/bin/env python3
"""RAG baseline comparison gate (P1-14, DI-003).

Compares a fresh offline evaluation run against a committed reference
baseline and fails on regressions. Retrieval change checklist step:

    python scripts/check_rag_baseline.py
    python scripts/check_rag_baseline.py --benchmark backend/tests/fixtures/rag_benchmark_v2.json

The gate NEVER writes to reference artifacts: the fresh run goes to a temp
file unless --json-out points elsewhere (refused when equal to --baseline).
Reference baselines are only read.

Exit codes: 0 pass · 1 regression detected · 2 invalid/incompatible inputs.
Offline: forces HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE, no network, no LLM,
no index rebuild. A passing gate is regression control on synthetic
labels, not proof of retrieval correctness.
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

# Offline first: never download a model or MITRE data from here.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

FIXTURES_DIR = BACKEND_DIR / "tests" / "fixtures"


class GateInputError(ValueError):
    """Missing, malformed, or inconsistent gate input files."""


def fail(message: str) -> NoReturn:
    print(f"FATAL: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_json_file(path: Path) -> dict:
    """Load a JSON object file; fail clearly instead of crashing."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise GateInputError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GateInputError(f"{path} is not valid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise GateInputError(f"{path} must contain a JSON object")
    return data


def resolve_paths(benchmark: Path, baseline: Path | None, json_out: Path | None):
    """Pick default baseline/current-output paths; guard reference artifacts."""
    baseline_path = baseline or benchmark.parent / benchmark.name.replace(
        "benchmark", "baseline")
    if json_out is None:
        tmp = tempfile.NamedTemporaryFile(
            prefix="rag_gate_current_", suffix=".json", delete=False)
        tmp.close()
        out_path = Path(tmp.name)
    else:
        out_path = json_out
    if out_path.resolve() == baseline_path.resolve():
        raise GateInputError(
            f"--json-out must not equal the reference baseline {baseline_path}")
    return baseline_path, out_path


def render_report(gate: dict, benchmark_version: str) -> str:
    lines = [f"# RAG baseline gate: {benchmark_version}", ""]
    if not gate["compatible"]:
        lines.append("INCOMPATIBLE COMPARISON — no regression verdict possible:")
        lines += [f"- {reason}" for reason in gate["incompatibilities"]]
        return "\n".join(lines)
    lines.append("Fingerprint (all must match):")
    for row in gate["fingerprint"]:
        lines.append(f"- {row['field']}: {'match' if row['match'] else 'DIFFERS'}")
    lines += ["", "| Metric | Baseline | Current | Delta | Result |",
              "|---|---:|---:|---:|---|"]
    for row in gate["metric_rows"]:
        lines.append(
            f"| {row['metric']} | {row['baseline']:.6f} | {row['current']:.6f} "
            f"| {row['delta']:+.6f} | {'PASS' if row['pass'] else 'FAIL'} |")
    lost = [r for r in gate["case_rows"]
            if not r["no_match"] and r["outcome"] == "relevance-lost"]
    shifted = [r for r in gate["case_rows"]
               if not r["no_match"] and r["outcome"] == "rank-shifted"]
    if lost:
        lines += ["", "Complete relevance losses (FAIL):"]
        lines += [f"- {r['case_id']}: reciprocal_rank {r['ref_rr']} -> {r['cur_rr']}"
                  for r in lost]
    if shifted:
        lines += ["", "Rank shifts (reported, not failed):"]
        lines += [f"- {r['case_id']}: reciprocal_rank {r['ref_rr']} -> {r['cur_rr']}"
                  for r in shifted]
    if gate["no_match_rows"]:
        lines += ["", "No-match max-score behavior:"]
        for r in gate["no_match_rows"]:
            lines.append(
                f"- {r['case_id']}: {r['ref_max_score']} -> {r['cur_max_score']} "
                f"({r['note']})")
    for note in gate["coverage_notes"]:
        lines.append(
            f"coverage baseline={note['coverage_baseline']} "
            f"current={note['coverage_current']} new_errors={note['new_errors']}")
    lines += ["", f"GATE {'PASS' if gate['passed'] else 'FAIL'}"]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="RAG baseline comparison gate")
    parser.add_argument("--benchmark", type=Path,
                        default=FIXTURES_DIR / "rag_benchmark_v1.json")
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--tolerance", type=float, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    from app.services.rag_evaluation import (
        BASELINE_TOLERANCE,
        compare_baselines,
        load_benchmark_file,
        run_benchmark,
    )
    from app.services.rag_service import RagService, clear_rag_cache

    try:
        baseline_path, out_path = resolve_paths(
            args.benchmark, args.baseline, args.json_out)
    except GateInputError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    try:
        dataset = load_benchmark_file(args.benchmark)
    except Exception as exc:
        print(f"FATAL: invalid benchmark ({exc})", file=sys.stderr)
        return 2
    try:
        reference = load_json_file(baseline_path)
    except GateInputError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    tolerance = BASELINE_TOLERANCE if args.tolerance is None else args.tolerance
    max_k = max(args.k)
    rag = RagService(enabled=True, top_k=max_k)
    try:
        status = rag.status()
        if status.get("status") != "ready":
            print(f"FATAL: local RAG index unavailable ({status.get('detail')})",
                  file=sys.stderr)
            return 2
        current_corpus = {
            "doc_count": status.get("doc_count"),
            "technique_count": status.get("technique_count"),
            "subtechnique_count": status.get("subtechnique_count"),
            "embedding_model": status.get("embedding_model"),
            "embedding_dim": status.get("embedding_dim"),
            "bundle_sha256": status.get("bundle_sha256"),
        }

        def retrieve(query: str, k: int):
            return [{"technique_id": r.technique_id, "score": r.score}
                    for r in rag.query(query, top_k=k)]

        report = run_benchmark(dataset["cases"], retrieve, list(args.k))
    finally:
        clear_rag_cache()

    current = {
        "benchmark_version": dataset["version"],
        "benchmark_sha256": dataset["sha256"],
        "k_values": report["k_values"],
        "n_cases": report["n_cases"],
        "coverage": report["coverage"],
        "errors": report["errors"],
        "metrics": report["aggregates"],
        "corpus": current_corpus,
        "cases": [
            {"case_id": c["case_id"], "no_match": c["no_match"],
             "reciprocal_rank": c["reciprocal_rank"],
             "scores": c["scores"]}
            for c in report["cases"]
        ],
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2, sort_keys=True)

    gate = compare_baselines(reference, current, tolerance)
    print(render_report(gate, dataset["version"]))
    print(f"\nCurrent run (not a reference): {out_path}")
    if not gate["compatible"]:
        return 2
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
