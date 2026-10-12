#!/usr/bin/env python3
"""Offline LLM-guard evaluation runner (P1-20, Track A synthetic only).

Runs the versioned synthetic fixture through the UNCHANGED production
validator and writes a deterministic versioned report. Measurement only:
exit 0 on a successful run regardless of confusion counts (this is not a
gate); exit 2 on malformed fixtures or I/O failures.

    python scripts/eval_guard_harness.py
    python scripts/eval_guard_harness.py --fixture backend/tests/fixtures/llm_guard_eval_v1.json \
        --out reports/llm_guard_eval/guard_eval_report_v1.json

Offline: no provider calls, no network, no API keys. Never logs prompts,
scores, or generated content beyond validator error keys and short
per-case outcomes (no free-text excerpts).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.guard_evaluation import (  # noqa: E402
    EVAL_VERSION,
    evaluate_cases,
    fixture_sha256,
    load_fixture_file,
)

DEFAULT_FIXTURE = BACKEND_DIR / "tests" / "fixtures" / "llm_guard_eval_v1.json"
DEFAULT_OUT = REPO_ROOT / "reports" / "llm_guard_eval" / "guard_eval_report_v1.json"


def _code_rev() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline LLM-guard evaluation")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    try:
        fixture = load_fixture_file(args.fixture)
    except Exception as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    results = evaluate_cases(fixture)
    report = {
        "evaluation_version": EVAL_VERSION,
        "fixture_version": fixture["version"],
        "fixture_sha256": fixture_sha256(args.fixture),
        "code_rev": _code_rev(),
        "command": f"python scripts/eval_guard_harness.py --fixture {args.fixture} --out {args.out}",
        "track": "A-synthetic-only",
        "results": results,
        "limitations": [
            "Synthetic inputs only; results describe guard behavior on the "
            "fixture, not real-model output distribution or semantic safety.",
            "Lexical accept/reject is measured against the predefined policy "
            "encoded in expected_lexical; semantic assessments are curated, "
            "not expert-validated. Track B (reviewed real-model samples) is "
            "unexecuted.",
            "No acceptance thresholds are set; confusion counts are descriptive.",
        ],
    }
    try:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"FATAL: cannot write report: {exc}", file=sys.stderr)
        return 2

    confusion = results["confusion"]
    print(f"cases={results['n_cases']} scored={confusion['n_scored']} "
          f"unassessable={len(results['unassessable_case_ids'])} "
          f"errored={len(results['errored_rows'])}")
    print(f"TP(reject)={confusion['tp_reject']} "
          f"FN(unsafe-accept)={confusion['fn_unsafe_acceptance']} "
          f"TN(accept)={confusion['tn_accept']} "
          f"FP(benign-reject)={confusion['fp_benign_rejection']}")
    print(f"unsafe-acceptance-rate={confusion['unsafe_acceptance_rate']} "
          f"benign-rejection-rate={confusion['benign_rejection_rate']} "
          f"rejection-rate={confusion['guard_rejection_rate']} "
          f"error-rate={confusion['validation_error_rate']}")
    print(f"semantic-gaps={len(results['semantic_gaps'])}: "
          f"{[g['case_id'] for g in results['semantic_gaps']]}")
    mismatches = [r["case_id"] for r in results["per_case"]
                  if r["assessable"] and not r["lexical_match"]]
    print(f"policy-mismatches={len(mismatches)}: {mismatches}")
    print(f"report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
