#!/usr/bin/env python3
"""Offline MITRE ATT&CK retrieval benchmark (P1-2, evaluation-first).

Runs the versioned synthetic benchmark in backend/tests/fixtures/
through the REAL local retrieval path (FAISS index + local MiniLM
embeddings) and records a reproducible baseline. Changes nothing about
ranking, filtering, or API contracts.

Offline guarantees:
- HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE are forced before any model load,
  so a missing cached model fails clearly instead of downloading.
- No network access, no index rebuild, no LLM calls.
- Missing/invalid index -> exit 2 with a clear message; never fabricated
  metrics. Per-case retrieval errors are reported, never silently dropped.

Usage (from the repository root):
    python scripts/eval_rag_benchmark.py
    python scripts/eval_rag_benchmark.py --k 1 3 5 --json-out backend/tests/fixtures/rag_baseline_v1.json

Outputs:
- Markdown summary to stdout.
- Machine-readable JSON baseline to --json-out (deterministic: sorted keys,
  no timings, fixed K order). Includes benchmark sha256, corpus fingerprint,
  provenance freshness, and metric definitions reference.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import NoReturn

# Offline first: never download a model or MITRE data from here.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

DEFAULT_BENCHMARK = BACKEND_DIR / "tests" / "fixtures" / "rag_benchmark_v1.json"
DEFAULT_JSON_OUT = BACKEND_DIR / "tests" / "fixtures" / "rag_baseline_v1.json"

METRIC_DEFINITIONS = {
    "reference": "backend/app/services/rag_evaluation.py module docstring",
    "precision@k": "relevant in top-K / min(K, returned); empty results score 0.0",
    "recall@k": "expected IDs retrieved in top-K / expected IDs",
    "mrr@k": "mean 1/rank of first relevant hit within top-K, else 0.0",
    "relevance": "exact ID match, or retrieved sub-technique Txxxx.yyy of an expected parent Txxxx (parent alone never satisfies a sub-technique expectation)",
    "duplicates": "deduplicated defensively, first occurrence kept",
    "no_match": "excluded from P/R/MRR; reported with n_returned and max_score",
    "coverage": "cases without retrieval error / total cases",
}


def fail(message: str) -> NoReturn:
    print(f"FATAL: {message}", file=sys.stderr)
    raise SystemExit(2)


def build_markdown(baseline: dict) -> str:
    m = baseline["metrics"]
    lines = [
        "# RAG Retrieval Baseline (rag-benchmark-v1)",
        "",
        f"Benchmark: {baseline['benchmark_version']} (sha256 `{baseline['benchmark_sha256'][:12]}...`)",
        f"K values: {', '.join(str(k) for k in baseline['k_values'])}",
        f"Cases: {baseline['n_cases']} ({baseline['n_evaluable']} evaluable, "
        f"{baseline['n_no_match']} no-match, {baseline['n_errors']} errors, "
        f"coverage {baseline['coverage']:.2f})",
        "",
        "## Corpus (retrieval target, not ground truth)",
        f"docs={baseline['corpus']['doc_count']} "
        f"({baseline['corpus']['technique_count']} techniques + "
        f"{baseline['corpus']['subtechnique_count']} sub-techniques), "
        f"model={baseline['corpus']['embedding_model']}, "
        f"dim={baseline['corpus']['embedding_dim']}",
        "",
        "## Knowledge freshness (informational; does not affect quality metrics)",
        f"built_at={baseline['freshness'].get('built_at')}, "
        f"age_status={baseline['freshness'].get('knowledge_age_status')}, "
        f"stale={baseline['freshness'].get('is_stale')}, "
        f"release={baseline['freshness'].get('attack_version')}",
        "",
        "## Quality metrics (synthetic labels; NOT expert-validated)",
        "| K | Precision@K | Recall@K | MRR@K |",
        "|---|---:|---:|---:|",
    ]
    for k in baseline["k_values"]:
        lines.append(
            f"| {k} | {m[f'precision@{k}']:.3f} | {m[f'recall@{k}']:.3f} | {m[f'mrr@{k}']:.3f} |"
        )
    lines += ["", "## No-match behavior (scores of returned results)", ""]
    if baseline["no_match"]:
        for entry in baseline["no_match"]:
            lines.append(
                f"- {entry['case_id']}: returned={entry['n_returned']}, "
                f"max_score={entry['max_score']}"
            )
    else:
        lines.append("- none")
    if baseline["errors"]:
        lines += ["", "## Retrieval errors", ""]
        for entry in baseline["errors"]:
            lines.append(f"- {entry['case_id']}: {entry['error']}")
    lines += [
        "",
        "_Labels are synthetic and ambiguous by design; treat this as a "
        "regression baseline for future retrieval changes, not as validated "
        "relevance truth._",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline RAG retrieval benchmark")
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--k", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args()

    from app.services.rag_evaluation import (
        BenchmarkError,
        load_benchmark_file,
        run_benchmark,
    )
    from app.services.rag_service import RagService, clear_rag_cache

    try:
        dataset = load_benchmark_file(args.benchmark)
    except BenchmarkError as e:
        fail(f"Invalid benchmark: {e}")

    max_k = max(args.k)
    rag = RagService(enabled=True, top_k=max_k)
    status = rag.status()
    if status.get("status") != "ready":
        fail(
            f"Local RAG index unavailable ({status.get('detail')}); "
            "refusing to fabricate a baseline."
        )
    corpus = {
        "doc_count": status.get("doc_count"),
        "technique_count": status.get("technique_count"),
        "subtechnique_count": status.get("subtechnique_count"),
        "embedding_model": status.get("embedding_model"),
        "embedding_dim": status.get("embedding_dim"),
        "index_path": status.get("index_path"),
        "bundle_sha256": status.get("bundle_sha256"),
    }
    freshness = {
        "source_url": status.get("source_url"),
        "built_at": status.get("built_at"),
        "max_modified": status.get("max_modified"),
        "attack_version": status.get("attack_version"),
        "knowledge_age_days": status.get("knowledge_age_days"),
        "knowledge_age_status": status.get("knowledge_age_status"),
        "is_stale": status.get("is_stale"),
    }

    def retrieve(query: str, k: int):
        return [
            {"technique_id": r.technique_id, "score": r.score}
            for r in rag.query(query, top_k=k)
        ]

    try:
        report = run_benchmark(dataset["cases"], retrieve, list(args.k))
    finally:
        clear_rag_cache()

    baseline = {
        "benchmark_version": dataset["version"],
        "benchmark_sha256": dataset["sha256"],
        "k_values": report["k_values"],
        "n_cases": report["n_cases"],
        "n_evaluable": report["n_evaluable"],
        "n_no_match": report["n_no_match"],
        "n_errors": report["n_errors"],
        "coverage": report["coverage"],
        "corpus": corpus,
        "freshness": freshness,
        "metric_definitions": METRIC_DEFINITIONS,
        "metrics": report["aggregates"],
        "no_match": report["no_match"],
        "errors": report["errors"],
        "cases": report["cases"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.json_out, "w", encoding="utf-8") as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(build_markdown(baseline))
    print(f"\nBaseline JSON: {args.json_out}")


if __name__ == "__main__":
    main()
