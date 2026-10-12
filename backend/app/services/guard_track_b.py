"""Track B measurement primitives (P1-25). Offline-only helpers.

`measure_track_b` scores human-annotated, previously captured provider
outputs through the UNCHANGED validator and the shared confusion math.
It performs no network I/O, invokes no provider, and refuses inputs
containing key material. Live capture is a separate, explicitly
authorized manual procedure (see LLM_GUARD_TRACK_B_EVALUATION_P1_25.md);
this module never performs it.
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from app.services import guard_evaluation as ge
from app.services.guard_evaluation import (
    GuardEvalError,
    confusion_matrix,
    run_case,
)

TRACK_B_VERSION = "llm-guard-track-b-v1"

# Refuse to persist anything shaped like a credential.
_SECRET_SHAPES = (
    re.compile(r"sk-[A-Za-z0-9]{8,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
    re.compile(r"xox[bap]-[A-Za-z0-9-]+"),
)


def _scan_for_secrets(text: str, where: str) -> None:
    for pattern in _SECRET_SHAPES:
        if pattern.search(text):
            raise GuardEvalError(
                f"Refusing {where}: input matches a secret shape; "
                "redact credentials before persisting Track B data"
            )


def load_manifest(path: Path) -> Dict[str, Any]:
    """Load and validate a Track B manifest (input set + annotation schema)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GuardEvalError(f"Manifest unreadable or invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardEvalError("Manifest must be a JSON object")
    if data.get("version") != TRACK_B_VERSION:
        raise GuardEvalError(f"Unsupported manifest version: {data.get('version')!r}")
    inputs = data.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise GuardEvalError("Manifest 'inputs' must be a non-empty list")
    seen = set()
    for pos, entry in enumerate(inputs):
        if not isinstance(entry, dict):
            raise GuardEvalError(f"Input at index {pos} is not an object")
        input_id = entry.get("input_id")
        if not isinstance(input_id, str) or not input_id.strip():
            raise GuardEvalError(f"Input at index {pos} lacks input_id")
        if input_id in seen:
            raise GuardEvalError(f"Duplicate input_id {input_id!r}")
        seen.add(input_id)
        for key in ("flow_ref", "task", "approval"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise GuardEvalError(f"Input {input_id!r} lacks {key}")
        # Retrieval context recorded at capture time (empty until captured).
        for key in ("allowed_ids", "allowed_mitigations"):
            if key in entry and not isinstance(entry[key], (dict, list)):
                raise GuardEvalError(f"Input {input_id!r} has malformed {key}")
        annotation = entry.get("human_annotation")
        if annotation is not None:
            if not isinstance(annotation, dict):
                raise GuardEvalError(f"Input {input_id!r} has malformed annotation")
            if annotation.get("lexical_expected") not in ("accept", "reject"):
                raise GuardEvalError(
                    f"Input {input_id!r}: lexical_expected must be accept/reject"
                )
            if annotation.get("semantic") not in ge.SEMANTIC_ASSESSMENTS:
                raise GuardEvalError(
                    f"Input {input_id!r}: unknown semantic assessment"
                )
            reviewer = annotation.get("reviewer")
            if not isinstance(reviewer, dict) or not reviewer.get("identity") \
                    or not reviewer.get("date"):
                raise GuardEvalError(
                    f"Input {input_id!r}: annotation needs reviewer identity+date"
                )
    return data


def load_captured_outputs(directory: Path, input_ids: List[str]) -> Dict[str, str]:
    """Load captured raw provider outputs (one <input_id>.json file each).

    Files must contain a JSON string (the raw provider output). Any file
    matching a secret shape is refused before parsing.
    """
    directory = Path(directory)
    captured: Dict[str, str] = {}
    missing = []
    for input_id in input_ids:
        path = directory / f"{input_id}.json"
        if not path.is_file():
            missing.append(input_id)
            continue
        try:
            blob = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise GuardEvalError(f"Cannot read {path}: {exc}") from exc
        _scan_for_secrets(blob, f"captured output {input_id!r}")
        try:
            raw = json.loads(blob)
        except json.JSONDecodeError as exc:
            raise GuardEvalError(f"Captured output {input_id!r} is not JSON: {exc}") from exc
        if not isinstance(raw, str):
            raise GuardEvalError(
                f"Captured output {input_id!r} must be a JSON string "
                "(raw provider output)"
            )
        captured[input_id] = raw
    if missing:
        raise GuardEvalError(
            f"No captured outputs for {len(missing)} input(s): {missing}. "
            "Track B requires an authorized capture run first."
        )
    return captured


def measure_track_b(
    manifest: Dict[str, Any],
    captured: Dict[str, str],
) -> Dict[str, Any]:
    """Score annotated Track B outputs; unannotated inputs are unassessable.

    Allowed IDs/mitigations come from each input's capture-time retrieval
    context (recorded in the manifest at capture). Only inputs carrying a
    human annotation enter confusion metrics; the rest are listed as
    pending review. Never invents labels.
    """
    rows: List[Dict[str, Any]] = []
    pending: List[str] = []
    for entry in manifest["inputs"]:
        input_id = entry["input_id"]
        annotation = entry.get("human_annotation")
        if annotation is None:
            pending.append(input_id)
            continue
        result = run_case(
            {"_raw": captured[input_id], "case_id": input_id},
            entry.get("allowed_ids", {}),
            entry.get("allowed_mitigations", []),
        )
        expected = annotation["lexical_expected"]
        observed = result["observed"]
        rows.append({
            "input_id": input_id,
            "task": entry["task"],
            "expected_lexical": expected,
            "observed": observed,
            "error_keys": result["error_keys"],
            "lexical_match": (
                (expected == "reject" and observed == "rejected")
                or (expected == "accept" and observed == "accepted")
            ),
            "semantic": annotation["semantic"],
            "reviewer": annotation["reviewer"],
        })
    # Reuse the shared confusion math via guard_evaluation row shape.
    confusion_rows = [{
        "case_id": r["input_id"],
        "expected_lexical": r["expected_lexical"],
        "observed": r["observed"],
    } for r in rows]
    return {
        "n_inputs": len(manifest["inputs"]),
        "n_annotated": len(rows),
        "n_pending_review": len(pending),
        "pending_review_ids": pending,
        "confusion": confusion_matrix(confusion_rows),
        "semantic_gaps": [
            {"input_id": r["input_id"], "semantic": r["semantic"],
             "error_keys": r["error_keys"]}
            for r in rows
            if r["observed"] == "accepted"
            and r["semantic"] in ge.SEMANTIC_GAP_ASSESSMENTS
        ],
        "errored": [r["input_id"] for r in rows if r["observed"] == "errored"],
        "per_input": rows,
    }


def readiness(provider_slug: str, key_present: bool, opt_in: bool,
              manifest_ok: bool) -> Dict[str, Any]:
    """Report Track B live-capture readiness without secrets or network."""
    blockers = []
    if not key_present:
        blockers.append("no provider credential configured")
    if not opt_in:
        blockers.append("explicit live-run authorization absent "
                         "(THREATWEAVE_TRACKB_LIVE=1 required)")
    if provider_slug not in ("openai", "mock"):
        blockers.append(f"unsupported provider {provider_slug!r}")
    if not manifest_ok:
        blockers.append("no valid approved input manifest")
    return {
        "ready": not blockers,
        "provider": provider_slug,
        "blockers": blockers,
    }
