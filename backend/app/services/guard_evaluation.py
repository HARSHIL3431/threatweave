"""Offline guard-evaluation harness (P1-20, DI-010/DI-006 measurement).

Measures what the existing validation layer accepts, rejects, errors on,
or leaves unassessable — without changing it. Pure functions over a
versioned synthetic fixture; no provider calls, no network, no new
dependencies. Lexical outcomes (accept/reject vs a predefined policy) are
kept separate from semantic assessments (unsafe/unsupported/needs-expert),
which synthetic inputs alone cannot establish as ground truth.

Positive class for confusion metrics: "should-reject" (expected reject).
An "errored" outcome (non-validation exception) is never a success and is
counted apart from rejections.
"""
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.llm_validation import validate_llm_output

EVAL_VERSION = "llm-guard-eval-v1"

LEXICAL_OUTCOMES = ("accept", "reject")
SEMANTIC_ASSESSMENTS = (
    "unsafe-recommendation",
    "unsupported-claim",
    "unsupported-attribution",
    "requires-expert-judgment",
    "supported-by-cited-mitigation",
    "no-safety-issue-apparent",
    "not-applicable-malformed",
)
# Semantic assessments that contradict a lexical "accept": the guard behaved
# as designed yet safety-relevant content passed (the lexical/semantic gap).
SEMANTIC_GAP_ASSESSMENTS = (
    "unsafe-recommendation",
    "unsupported-claim",
    "unsupported-attribution",
)


class GuardEvalError(ValueError):
    """Raised for malformed evaluation fixtures (fails clearly, never silent)."""


def fixture_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_fixture_file(path: Path) -> Dict[str, Any]:
    """Load and strictly validate an evaluation fixture."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GuardEvalError(f"Fixture unreadable or invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardEvalError("Fixture must be a JSON object")
    if data.get("version") != EVAL_VERSION:
        raise GuardEvalError(
            f"Unsupported fixture version: {data.get('version')!r}"
        )
    defaults = data.get("defaults")
    if not isinstance(defaults, dict):
        raise GuardEvalError("Fixture 'defaults' must be an object")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise GuardEvalError("Fixture 'cases' must be a non-empty list")
    seen = set()
    for pos, case in enumerate(cases):
        _validate_case(case, pos, seen)
    return data


def _validate_case(case: Any, pos: int, seen: set) -> None:
    def _fail(msg: str) -> None:
        raise GuardEvalError(f"Case at index {pos}: {msg}")

    if not isinstance(case, dict):
        _fail("not an object")
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        _fail("missing case_id")
    if case_id in seen:
        _fail(f"duplicate case_id {case_id!r}")
    seen.add(case_id)
    for key in ("category", "severity"):
        if not isinstance(case.get(key), str) or not case[key].strip():
            _fail(f"missing {key}")
    if case.get("qualified") not in (True, False, None):
        _fail("qualified must be true/false/null")
    if not isinstance(case.get("features", []), list):
        _fail("features must be a list")
    sources = [k for k in ("output", "output_patch", "raw") if k in case]
    if len(sources) != 1:
        _fail("exactly one of output/output_patch/raw is required")
    expected = case.get("expected_lexical")
    if not isinstance(expected, dict):
        _fail("expected_lexical must be an object")
    if expected.get("outcome") not in LEXICAL_OUTCOMES:
        _fail("expected_lexical.outcome must be accept/reject")
    if case.get("assessability", "assessable") not in ("assessable", "unassessable"):
        _fail("assessability must be assessable/unassessable")
    semantic = case.get("semantic")
    if not isinstance(semantic, dict):
        _fail("semantic must be an object")
    if semantic.get("assessment") not in SEMANTIC_ASSESSMENTS:
        _fail(f"unknown semantic assessment {semantic.get('assessment')!r}")
    if not isinstance(semantic.get("rationale"), str) or not semantic["rationale"].strip():
        _fail("semantic.rationale required")


def _resolve_raw(case: Dict[str, Any], defaults: Dict[str, Any]) -> Any:
    if "raw" in case:
        return case["raw"]
    if "output" in case:
        if not isinstance(case["output"], dict):
            raise GuardEvalError(f"Case {case['case_id']!r}: output must be an object")
        return json.dumps(case["output"])
    patch = case["output_patch"]
    base = defaults.get("output")
    if not isinstance(patch, dict) or not isinstance(base, dict):
        raise GuardEvalError(
            f"Case {case['case_id']!r}: output_patch needs a defaults.output object"
        )
    merged = dict(base)
    merged.update(patch)
    return json.dumps(merged)


def run_case(
    case: Dict[str, Any],
    allowed_ids: Dict[str, str],
    allowed_mitigations: List[str],
) -> Dict[str, Any]:
    """Run one fixture case through the unchanged validator.

    Returns observed outcome (accepted/rejected/errored) with error keys.
    Non-validation exceptions become "errored" — never successes.
    """
    from app.core.exceptions import LLMValidationErrorException

    raw = case["_raw"]
    try:
        validate_llm_output(raw, allowed_ids, allowed_mitigations)
        return {"observed": "accepted", "error_keys": []}
    except LLMValidationErrorException as exc:
        details = exc.details if isinstance(exc.details, dict) else {}
        return {"observed": "rejected", "error_keys": sorted(details)}
    except Exception as exc:  # never a successful validation
        return {"observed": "errored", "error_keys": [exc.__class__.__name__]}


def evaluate_cases(fixture: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate every fixture case; deterministic per-case rows + aggregates."""
    defaults = fixture["defaults"]
    rows: List[Dict[str, Any]] = []
    for case in fixture["cases"]:
        allowed_ids = case.get("allowed_ids", defaults.get("allowed_ids", {}))
        allowed_mits = case.get(
            "allowed_mitigations", defaults.get("allowed_mitigations", [])
        )
        work = dict(case)
        work["_raw"] = _resolve_raw(case, defaults)
        result = run_case(work, allowed_ids, allowed_mits)
        expected = case["expected_lexical"]["outcome"]
        assessable = case.get("assessability", "assessable") == "assessable"
        observed = result["observed"]
        lexical_match = assessable and (
            (expected == "reject" and observed == "rejected")
            or (expected == "accept" and observed == "accepted")
        )
        rows.append({
            "case_id": case["case_id"],
            "category": case["category"],
            "severity": case["severity"],
            "qualified": case.get("qualified"),
            "features": list(case.get("features", [])),
            "assessable": assessable,
            "expected_lexical": expected,
            "expected_error_key": case["expected_lexical"].get("error_key"),
            "observed": result["observed"],
            "error_keys": result["error_keys"],
            "lexical_match": lexical_match,
            "semantic": case["semantic"]["assessment"],
        })
    return {
        "n_cases": len(rows),
        "confusion": confusion_matrix([r for r in rows if r["assessable"]]),
        "stratified": {
            key: stratify([r for r in rows if r["assessable"]], key)
            for key in ("category", "severity", "qualified")
        },
        "semantic_gaps": [
            {"case_id": r["case_id"], "category": r["category"],
             "semantic": r["semantic"], "error_keys": r["error_keys"]}
            for r in rows
            if r["observed"] == "accepted"
            and r["semantic"] in SEMANTIC_GAP_ASSESSMENTS
        ],
        "unassessable_case_ids": [r["case_id"] for r in rows if not r["assessable"]],
        "errored_rows": [
            {"case_id": r["case_id"], "error_keys": r["error_keys"]}
            for r in rows if r["observed"] == "errored"
        ],
        "per_case": rows,
    }


def confusion_matrix(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """TP/FN/TN/FP with positive class = should-reject.

    Rates are None on empty denominators (no evidence either way).
    """
    tp = sum(1 for r in rows if r["expected_lexical"] == "reject"
             and r["observed"] == "rejected")
    fn = sum(1 for r in rows if r["expected_lexical"] == "reject"
             and r["observed"] == "accepted")
    tn = sum(1 for r in rows if r["expected_lexical"] == "accept"
             and r["observed"] == "accepted")
    fp = sum(1 for r in rows if r["expected_lexical"] == "accept"
             and r["observed"] == "rejected")
    n_should_reject = tp + fn
    n_should_accept = tn + fp
    n_scored = len(rows)
    n_rejected = sum(1 for r in rows if r["observed"] == "rejected")
    n_errored = sum(1 for r in rows if r["observed"] == "errored")

    def _rate(k: int, n: int) -> Optional[float]:
        return (k / n) if n else None

    return {
        "n_scored": n_scored,
        "tp_reject": tp,
        "fn_unsafe_acceptance": fn,
        "tn_accept": tn,
        "fp_benign_rejection": fp,
        "unsafe_acceptance_rate": _rate(fn, n_should_reject),
        "unsafe_acceptance_ci95": wilson_interval(fn, n_should_reject),
        "benign_rejection_rate": _rate(fp, n_should_accept),
        "benign_rejection_ci95": wilson_interval(fp, n_should_accept),
        "guard_rejection_rate": _rate(n_rejected, n_scored),
        "validation_error_rate": _rate(n_errored, n_scored),
    }


def stratify(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    """Confusion summaries per distinct value of a row key."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(key)), []).append(row)
    return {name: confusion_matrix(members) for name, members in sorted(groups.items())}


def wilson_interval(k: int, n: int, z: float = 1.96) -> List[Optional[float]]:
    """Wilson 95% interval for a rate; [None, None] when n is 0."""
    if not n:
        return [None, None]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [max(0.0, center - half), min(1.0, center + half)]
