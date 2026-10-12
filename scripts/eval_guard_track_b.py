#!/usr/bin/env python3
"""Track B guard-evaluation runner (P1-25). Offline-first, no exceptions.

Subcommands (all offline; NOTHING here performs network I/O or calls a
provider — there is deliberately no live-capture code path):

    readiness   Report live-capture readiness (provider slug, key presence
                as boolean only, opt-in flag, manifest validity). Exit 0.
    measure     Score previously captured, human-annotated provider outputs
                through the unchanged validator; write a versioned report.
                Fails clearly when outputs/annotations are absent.

    python scripts/eval_guard_track_b.py readiness
    python scripts/eval_guard_track_b.py measure --manifest backend/tests/fixtures/llm_guard_track_b_manifest_v1.json \
        --outputs-dir <approved-captures> --out reports/llm_guard_eval/guard_track_b_report_v1.json
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

from app.services.guard_track_b import (  # noqa: E402
    TRACK_B_VERSION,
    GuardEvalError,
    load_captured_outputs,
    load_manifest,
    measure_track_b,
    readiness,
)

DEFAULT_MANIFEST = (BACKEND_DIR / "tests" / "fixtures"
                    / "llm_guard_track_b_manifest_v1.json")
DEFAULT_OUT = REPO_ROOT / "reports" / "llm_guard_eval" / "guard_track_b_report_v1.json"

TRACK_B_OPT_IN = "THREATWEAVE_TRACKB_LIVE"


def _code_rev() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _provider_slug() -> str:
    return (os.environ.get("LLM_PROVIDER") or "openai").strip().lower()


def cmd_readiness(_args) -> int:
    try:
        manifest = load_manifest(DEFAULT_MANIFEST)
        manifest_ok = True
    except GuardEvalError as exc:
        print(f"manifest: INVALID ({exc})")
        manifest_ok = False
    report = readiness(
        provider_slug=_provider_slug(),
        key_present=bool(os.environ.get("LLM_API_KEY")),
        opt_in=os.environ.get(TRACK_B_OPT_IN) == "1",
        manifest_ok=manifest_ok,
    )
    print(f"provider: {report['provider']}")
    print(f"credential configured: {'yes' if bool(os.environ.get('LLM_API_KEY')) else 'no'} "
          "(presence only — value never displayed)")
    print(f"live-run opt-in ({TRACK_B_OPT_IN}=1): "
          f"{'yes' if os.environ.get(TRACK_B_OPT_IN) == '1' else 'no'}")
    if report["ready"]:
        print("TRACK B READY: manifest valid; capture may proceed only under "
              "explicit owner authorization with the documented procedure.")
    else:
        print("TRACK B BLOCKED:")
        for blocker in report["blockers"]:
            print(f"  - {blocker}")
        print("No live calls were made. See "
              "docs/reliability/LLM_GUARD_TRACK_B_EVALUATION_P1_25.md.")
    return 0


def cmd_measure(args) -> int:
    try:
        manifest = load_manifest(args.manifest)
    except GuardEvalError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    input_ids = [e["input_id"] for e in manifest["inputs"]]
    try:
        captured = load_captured_outputs(args.outputs_dir, input_ids)
    except GuardEvalError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    try:
        results = measure_track_b(manifest, captured)
    except GuardEvalError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2
    report = {
        "evaluation_version": TRACK_B_VERSION,
        "manifest_version": manifest["version"],
        "code_rev": _code_rev(),
        "command": "python scripts/eval_guard_track_b.py measure",
        "track": "B-captured-outputs",
        "results": results,
        "limitations": [
            "Only human-annotated captured outputs enter confusion metrics; "
            "pending inputs are listed, never scored.",
            "Lexical outcomes measure guard behavior, not semantic safety; "
            "ambiguous cases require the recorded human review.",
            "No acceptance thresholds are set.",
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
    print(f"inputs={results['n_inputs']} annotated={results['n_annotated']} "
          f"pending={results['n_pending_review']} errored={len(results['errored'])}")
    print(f"TP={confusion['tp_reject']} FN={confusion['fn_unsafe_acceptance']} "
          f"TN={confusion['tn_accept']} FP={confusion['fp_benign_rejection']}")
    print(f"report: {args.out}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Track B guard evaluation")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("readiness", help="report live-capture readiness (offline)")
    measure = sub.add_parser("measure", help="score captured annotated outputs")
    measure.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    measure.add_argument("--outputs-dir", type=Path, required=True)
    measure.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if args.command == "readiness":
        return cmd_readiness(args)
    return cmd_measure(args)


if __name__ == "__main__":
    raise SystemExit(main())
