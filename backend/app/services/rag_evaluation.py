"""Deterministic offline evaluation for MITRE ATT&CK retrieval relevance (P1-2).

Evaluation-first scaffolding: measures the *existing* retrieval pipeline,
changes nothing about ranking, filtering, or API contracts. Pure functions
plus a runner over an injected retrieval callable, so metric arithmetic is
testable without a model and the production baseline runs through the real
local path (FAISS index + local embeddings, no network, no LLM).

Metric policies (see module docstring of the benchmark for label honesty):
- Relevance: exact technique-ID match, or a retrieved sub-technique
  ``Txxxx.yyy`` when its parent ``Txxxx`` is expected. A retrieved parent
  does NOT satisfy a sub-technique expectation (insufficient specificity).
- Precision@K denominator is ``min(K, results returned)``; empty results
  score 0.0 (no precision achievable).
- Recall@K is over the case's expected-ID set.
- MRR@K uses the first relevant result within the top K (1-based); cases
  with no relevant hit in range contribute 0.0. ``no_match`` cases are
  excluded from P/R/MRR entirely and reported separately with scores.
- Duplicate technique IDs in results are deduplicated defensively (first
  occurrence rank kept); the production pipeline cannot emit duplicates
  (positional mapping + P0-2 unique-ID enforcement).
- Retrieval exceptions mark the case as an error: excluded from quality
  aggregates, counted against coverage. Malformed benchmark records fail
  the whole validation loudly instead of being silently dropped.

P1-4 adds pure no-match policy helpers (score floor / top-score margin plus
a trade-off evaluator over recorded results). They are evaluation tooling
only and are deliberately NOT connected to the production retrieval path.

P1-14 adds a baseline comparison gate (compare_baselines): a committed
reference baseline vs a fresh run, with fingerprint equality, metric
regression detection, per-case relevance-loss detection, and no-match
behavior comparison. A passing gate is regression control, not proof of
retrieval correctness on synthetic labels.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

TECHNIQUE_ID_RE = re.compile(r"^T\d{4}(\.\d{3})?$")

BENCHMARK_VERSION = "rag-benchmark-v1"
SUPPORTED_BENCHMARK_VERSIONS = ("rag-benchmark-v1", "rag-benchmark-v2")

_CASE_KEYS = {
    "case_id", "query", "expected_ids", "no_match",
    "label_provenance", "rationale", "ambiguity",
}


class BenchmarkError(ValueError):
    """Raised for malformed benchmark data or unusable retrieval."""


def _parent_of(technique_id: str) -> Optional[str]:
    if "." in technique_id:
        return technique_id.split(".", 1)[0]
    return None


def is_relevant(retrieved_id: Any, expected_ids: List[str]) -> bool:
    """Apply the parent/sub-technique relevance policy."""
    if not isinstance(retrieved_id, str) or retrieved_id not in expected_ids:
        parent = _parent_of(retrieved_id) if isinstance(retrieved_id, str) else None
        return parent is not None and parent in expected_ids
    return True


def dedupe_ids(retrieved_ids: List[str]) -> List[str]:
    """Defensive dedupe preserving first-occurrence order."""
    seen: List[str] = []
    for tid in retrieved_ids:
        if tid not in seen:
            seen.append(tid)
    return seen


def precision_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    top = dedupe_ids(retrieved_ids)[: max(1, k)]
    if not top:
        return 0.0
    hits = sum(1 for tid in top if is_relevant(tid, expected_ids))
    return hits / len(top)


def recall_at_k(retrieved_ids: List[str], expected_ids: List[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    top = set(dedupe_ids(retrieved_ids)[: max(1, k)])
    hits = sum(1 for exp in expected_ids if exp in top or any(
        _parent_of(tid) == exp for tid in top
    ))
    return hits / len(expected_ids)


def reciprocal_rank(retrieved_ids: List[str], expected_ids: List[str], k: Optional[int] = None) -> float:
    """Reciprocal rank of the first relevant result (1-based), else 0.0.

    When ``k`` is given, only the top-K results are considered.
    """
    ids = dedupe_ids(retrieved_ids)
    if k is not None:
        ids = ids[: max(1, k)]
    for rank, tid in enumerate(ids, start=1):
        if is_relevant(tid, expected_ids):
            return 1.0 / rank
    return 0.0


def validate_benchmark(data: Any) -> Dict[str, Any]:
    """Validate a parsed benchmark document; fail loudly on any defect."""
    if not isinstance(data, dict):
        raise BenchmarkError("Benchmark must be a JSON object")
    if data.get("version") not in SUPPORTED_BENCHMARK_VERSIONS:
        raise BenchmarkError(
            f"Unsupported benchmark version: {data.get('version')!r}"
        )
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise BenchmarkError("Benchmark 'cases' must be a non-empty list")
    seen_ids = set()
    for pos, case in enumerate(cases):
        if not isinstance(case, dict):
            raise BenchmarkError(f"Case at index {pos} is not an object")
        unknown = set(case) - _CASE_KEYS
        if unknown:
            raise BenchmarkError(
                f"Case {case.get('case_id', pos)!r} has unknown keys: {sorted(unknown)}"
            )
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise BenchmarkError(f"Case at index {pos} has no valid case_id")
        if case_id in seen_ids:
            raise BenchmarkError(f"Duplicate case_id {case_id!r}")
        seen_ids.add(case_id)
        if not isinstance(case.get("query"), str) or not case["query"].strip():
            raise BenchmarkError(f"Case {case_id!r} has no valid query")
        expected = case.get("expected_ids")
        if not isinstance(expected, list) or not all(
            isinstance(t, str) and TECHNIQUE_ID_RE.match(t) for t in expected
        ):
            raise BenchmarkError(
                f"Case {case_id!r} has invalid expected_ids (Txxxx[.yyy] strings required)"
            )
        if not isinstance(case.get("no_match"), bool):
            raise BenchmarkError(f"Case {case_id!r} has no boolean no_match flag")
        if case["no_match"] and expected:
            raise BenchmarkError(
                f"Case {case_id!r} is no_match but lists expected_ids"
            )
        if not case["no_match"] and not expected:
            raise BenchmarkError(
                f"Case {case_id!r} has no expected_ids and is not no_match"
            )
        if case.get("label_provenance") != "synthetic":
            raise BenchmarkError(
                f"Case {case_id!r} must declare label_provenance 'synthetic' "
                "(expert validation must not be claimed without evidence)"
            )
        if not isinstance(case.get("rationale"), str) or not case["rationale"].strip():
            raise BenchmarkError(f"Case {case_id!r} has no rationale")
    return {"version": data["version"], "cases": cases}


def load_benchmark_file(path: Path) -> Dict[str, Any]:
    """Read and validate a benchmark JSON file, returning dataset + sha256."""
    raw = Path(path).read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise BenchmarkError(f"Benchmark file is not valid JSON: {e}") from e
    dataset = validate_benchmark(data)
    dataset["sha256"] = hashlib.sha256(raw).hexdigest()
    dataset["source_path"] = str(path)
    return dataset


@dataclass
class CaseResult:
    """Per-case outcome; scores kept for no-match analysis."""

    case_id: str
    no_match: bool
    retrieved_ids: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    per_k: Dict[int, Dict[str, float]] = field(default_factory=dict)
    reciprocal_rank: float = 0.0
    error: Optional[str] = None


def evaluate_case(
    case: Dict[str, Any],
    retrieved: List[Dict[str, Any]],
    k_values: List[int],
) -> CaseResult:
    """Score one case against retrieved [{technique_id, score}] records."""
    ids = [r.get("technique_id") for r in retrieved]
    scores = [float(r.get("score", 0.0)) for r in retrieved]
    result = CaseResult(
        case_id=case["case_id"], no_match=case["no_match"],
        retrieved_ids=ids, scores=scores,
    )
    if case["no_match"]:
        return result
    expected = case["expected_ids"]
    for k in k_values:
        result.per_k[k] = {
            "precision": precision_at_k(ids, expected, k),
            "recall": recall_at_k(ids, expected, k),
            "mrr": reciprocal_rank(ids, expected, k),
        }
    result.reciprocal_rank = reciprocal_rank(ids, expected)
    return result


def run_benchmark(
    cases: List[Dict[str, Any]],
    retrieve_fn: Callable[[str, int], List[Dict[str, Any]]],
    k_values: List[int],
) -> Dict[str, Any]:
    """Run every case through ``retrieve_fn``; deterministic aggregate output.

    ``retrieve_fn(query, k)`` returns [{technique_id, score}]. Retrieval
    exceptions are captured per case (error recorded, quality metrics
    skipped, coverage penalized) — never silently dropped, never fabricated.
    """
    k_values = sorted({max(1, int(k)) for k in k_values})
    max_k = max(k_values)
    results: List[CaseResult] = []
    for case in cases:
        try:
            retrieved = retrieve_fn(case["query"], max_k) or []
            if not isinstance(retrieved, list):
                raise BenchmarkError("retrieve_fn must return a list")
            results.append(evaluate_case(case, retrieved, k_values))
        except BenchmarkError:
            raise
        except Exception as e:  # per-case capture; keeps the failure visible
            results.append(CaseResult(
                case_id=case["case_id"], no_match=bool(case.get("no_match")),
                error=f"{e.__class__.__name__}",
            ))

    evaluable = [r for r in results if r.error is None and not r.no_match]
    aggregates: Dict[str, Any] = {}
    for k in k_values:
        aggregates[f"precision@{k}"] = (
            sum(r.per_k[k]["precision"] for r in evaluable) / len(evaluable)
            if evaluable else 0.0
        )
        aggregates[f"recall@{k}"] = (
            sum(r.per_k[k]["recall"] for r in evaluable) / len(evaluable)
            if evaluable else 0.0
        )
        aggregates[f"mrr@{k}"] = (
            sum(r.per_k[k]["mrr"] for r in evaluable) / len(evaluable)
            if evaluable else 0.0
        )
    no_match = [
        {
            "case_id": r.case_id,
            "n_returned": len(r.retrieved_ids),
            "max_score": max(r.scores) if r.scores else None,
        }
        for r in results if r.no_match and r.error is None
    ]
    errors = [
        {"case_id": r.case_id, "error": r.error}
        for r in results if r.error is not None
    ]
    return {
        "k_values": k_values,
        "n_cases": len(cases),
        "n_evaluable": len(evaluable),
        "n_no_match": len(no_match),
        "n_errors": len(errors),
        "coverage": (len(cases) - len(errors)) / len(cases) if cases else 0.0,
        "aggregates": aggregates,
        "no_match": no_match,
        "errors": errors,
        "cases": [
            {
                "case_id": r.case_id,
                "no_match": r.no_match,
                "retrieved_ids": r.retrieved_ids,
                "scores": [round(s, 4) for s in r.scores],
                "per_k": {str(k): v for k, v in r.per_k.items()},
                "reciprocal_rank": round(r.reciprocal_rank, 4),
                "error": r.error,
            }
            for r in results
        ],
    }

# ---------------------------------------------------------------------------
# Label-review validation (P1-6). Offline, deterministic checks over the
# analyst adjudication queue (rag_label_review_v1.json). The queue tracks
# review state per (benchmark_version, case_id); it never changes benchmark
# labels or evaluator semantics. Automated proposals are attributed and can
# never count as human approval: a record is decided only with reviewer
# identity, date, decision, and rationale all present.
# ---------------------------------------------------------------------------

REVIEW_SCHEMA_VERSION = "rag-label-review-v1"
REVIEW_STATUSES = ("pending", "decided")
REVIEW_DECISIONS = ("accept", "revise", "reject", "needs-domain-review")
REVIEW_CHANGE_TYPES = ("label", "schema")


class ReviewError(ValueError):
    """Raised for malformed review records or coverage gaps."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewError(message)


def validate_review_queue(
    review: Any,
    benchmark_cases: Dict[tuple, Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate a label-review queue against benchmark source cases.

    ``benchmark_cases`` maps (benchmark_version, case_id) -> benchmark case
    dict and defines the exact expected coverage. Returns a summary with
    counts by status/decision. Raises ReviewError on any defect; nothing is
    silently repaired or dropped.
    """
    _require(isinstance(review, dict), "Review queue must be a JSON object")
    _require(
        review.get("version") == REVIEW_SCHEMA_VERSION,
        f"Unsupported review version: {review.get('version')!r}",
    )
    records = review.get("records")
    _require(isinstance(records, list) and records,
             "Review queue 'records' must be a non-empty list")

    seen = set()
    by_status: Dict[str, int] = {}
    proposed_changes = 0
    for pos, rec in enumerate(records):
        _require(isinstance(rec, dict), f"Record at index {pos} is not an object")
        version = rec.get("benchmark_version")
        case_id = rec.get("case_id")
        key = (version, case_id)
        _require(isinstance(version, str) and isinstance(case_id, str),
                 f"Record at index {pos} lacks version/case_id strings")
        _require(key not in seen, f"Duplicate review entry for {version}/{case_id}")
        seen.add(key)
        _require(key in benchmark_cases,
                 f"Review entry {version}/{case_id} resolves to no source case")
        source = benchmark_cases[key]

        original = rec.get("original")
        _require(isinstance(original, dict), f"{case_id}: original block missing")
        _require(original.get("query") == source.get("query"),
                 f"{case_id}: original query does not match source fixture")
        _require(original.get("expected_ids") == source.get("expected_ids"),
                 f"{case_id}: original expected_ids do not match source fixture")
        _require(original.get("no_match") == source.get("no_match"),
                 f"{case_id}: original no_match does not match source fixture")

        status = rec.get("status")
        _require(status in REVIEW_STATUSES,
                 f"{case_id}: invalid status {status!r}")

        proposal = rec.get("automated_proposal")
        _require(isinstance(proposal, dict), f"{case_id}: automated_proposal missing")
        _require(proposal.get("outcome") in REVIEW_DECISIONS,
                 f"{case_id}: invalid proposed outcome")
        _require(proposal.get("analyzer") == "automated-analysis",
                 f"{case_id}: automated proposal must be attributed")
        _require(isinstance(proposal.get("rationale"), str)
                 and proposal["rationale"].strip(),
                 f"{case_id}: automated proposal needs a rationale")

        change = rec.get("proposed_change")
        if change is not None:
            _require(isinstance(change, dict)
                     and change.get("type") in REVIEW_CHANGE_TYPES
                     and isinstance(change.get("detail"), str)
                     and change["detail"].strip(),
                     f"{case_id}: malformed proposed_change")
            proposed_changes += 1

        reviewer = rec.get("reviewer")
        _require(isinstance(reviewer, dict), f"{case_id}: reviewer block missing")
        identity = reviewer.get("identity")
        date = reviewer.get("date")
        decision = reviewer.get("decision")
        rationale = reviewer.get("rationale")
        if status == "pending":
            _require(decision is None and identity is None
                     and date is None and rationale is None,
                     f"{case_id}: pending records must carry no human decision "
                     "or sign-off (automated proposals are not approvals)")
        else:
            _require(decision in REVIEW_DECISIONS
                     and isinstance(identity, str) and identity.strip()
                     and isinstance(date, str) and date.strip()
                     and isinstance(rationale, str) and rationale.strip(),
                     f"{case_id}: decided records require reviewer identity, "
                     "date, decision, and rationale")
        by_status[status] = by_status.get(status, 0) + 1

    missing = [f"{v}/{c}" for (v, c) in benchmark_cases if (v, c) not in seen]
    _require(not missing,
             f"Review queue misses {len(missing)} benchmark cases: {missing[:5]}")

    return {
        "n_records": len(records),
        "n_expected": len(benchmark_cases),
        "by_status": by_status,
        "n_pending": by_status.get("pending", 0),
        "n_decided": by_status.get("decided", 0),
        "n_proposed_changes": proposed_changes,
    }



# ---------------------------------------------------------------------------
# No-match policy evaluation (P1-4). Pure offline helpers operating on
# recorded retrieved [{technique_id, score}] lists. These are NOT wired into
# the production retrieval path: no production threshold exists, and a good
# score on a synthetic benchmark alone does not justify creating one
# (see DI-002). Policies here quantify trade-offs for the recommendation.
# ---------------------------------------------------------------------------

def apply_score_floor(
    retrieved: List[Dict[str, Any]], floor: float
) -> List[Dict[str, Any]]:
    """Keep results with score >= floor, preserving order."""
    return [r for r in retrieved if float(r.get("score", 0.0)) >= floor]


def apply_score_margin(
    retrieved: List[Dict[str, Any]], margin: float
) -> List[Dict[str, Any]]:
    """Keep results within margin of the top score, preserving order."""
    if not retrieved:
        return []
    top = max(float(r.get("score", 0.0)) for r in retrieved)
    return [r for r in retrieved if float(r.get("score", 0.0)) >= top - margin]


def evaluate_policy(
    cases: List[Dict[str, Any]],
    retrieved_by_case: Dict[str, List[Dict[str, Any]]],
    policy_fn: Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Quantify one no-match policy off recorded retrieval results.

    For evaluable cases: fraction keeping at least one relevant result
    (kept-relevant rate) and mean kept count. For no-match cases: fraction
    fully suppressed. Cases missing from ``retrieved_by_case`` are errors:
    counted, never silently dropped.
    """
    per_case: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for case in cases:
        if case["case_id"] not in retrieved_by_case:
            errors.append({"case_id": case["case_id"], "error": "no recorded results"})
            continue
        kept = policy_fn(retrieved_by_case[case["case_id"]]) or []
        kept_ids = [r.get("technique_id") for r in kept]
        entry: Dict[str, Any] = {
            "case_id": case["case_id"],
            "no_match": case["no_match"],
            "n_kept": len(kept),
        }
        if case["no_match"]:
            entry["fully_suppressed"] = len(kept) == 0
        else:
            entry["kept_relevant"] = any(
                is_relevant(tid, case["expected_ids"]) for tid in kept_ids
            )
        per_case.append(entry)

    evaluable = [e for e in per_case if not e["no_match"]]
    nomatch = [e for e in per_case if e["no_match"]]
    return {
        "n_cases": len(cases),
        "n_evaluable": len(evaluable),
        "n_no_match": len(nomatch),
        "n_errors": len(errors),
        "kept_relevant_rate": (
            sum(1 for e in evaluable if e["kept_relevant"]) / len(evaluable)
            if evaluable else 0.0
        ),
        "mean_kept_evaluable": (
            sum(e["n_kept"] for e in evaluable) / len(evaluable)
            if evaluable else 0.0
        ),
        "no_match_suppression_rate": (
            sum(1 for e in nomatch if e["fully_suppressed"]) / len(nomatch)
            if nomatch else 0.0
        ),
        "errors": errors,
        "per_case": per_case,
    }


# ---------------------------------------------------------------------------
# Threshold re-derivation support (P1-16, DI-012). Pure offline helpers for a
# FUTURE threshold decision on human-adjudicated labels. Nothing here runs in
# production, selects a threshold value, or treats synthetic labels as
# authoritative: callers supply adjudicated per-case labels explicitly, and
# unresolved cases are excluded from primary metrics (counted, with their
# scores exposed for sensitivity analysis). Comparison convention is
# ``score >= threshold``, matching ``apply_score_floor``; compare on stored
# scores (6-decimal production precision), never on re-rounded display text.
# ---------------------------------------------------------------------------

#: Adjudicated label statuses for threshold derivation. ``relevant`` means a
#: human confirmed at least one technique is described; ``no_match`` means a
#: human confirmed none is; ``unresolved`` covers ambiguous,
#: insufficient-evidence, and disagreed cases (excluded from primary metrics).
THRESHOLD_LABEL_STATUSES = ("relevant", "no_match", "unresolved")


class ThresholdError(ValueError):
    """Raised for malformed threshold-derivation inputs or leaking splits."""


def _threshold_case_label(case: Any, pos: int) -> Dict[str, Any]:
    """Validate one adjudicated label record; raise ThresholdError if unfit."""
    if not isinstance(case, dict):
        raise ThresholdError(f"Labeled case at index {pos} is not an object")
    case_id = case.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ThresholdError(f"Labeled case at index {pos} has no valid case_id")
    status = case.get("status")
    if status not in THRESHOLD_LABEL_STATUSES:
        raise ThresholdError(
            f"Case {case_id!r} has invalid label status {status!r} "
            f"(expected one of {THRESHOLD_LABEL_STATUSES})"
        )
    relevant_ids = case.get("relevant_ids", [])
    if not isinstance(relevant_ids, list) or not all(
        isinstance(t, str) and TECHNIQUE_ID_RE.match(t) for t in relevant_ids
    ):
        raise ThresholdError(
            f"Case {case_id!r} has invalid relevant_ids "
            "(Txxxx[.yyy] strings required)"
        )
    if status == "relevant" and not relevant_ids:
        raise ThresholdError(
            f"Case {case_id!r} is labeled relevant but lists no relevant_ids"
        )
    if status == "no_match" and relevant_ids:
        raise ThresholdError(
            f"Case {case_id!r} is labeled no_match but lists relevant_ids"
        )
    return {"case_id": case_id, "status": status, "relevant_ids": relevant_ids}


def evaluate_candidate_threshold(
    labeled_cases: List[Dict[str, Any]],
    retrieved_by_case: Dict[str, List[Dict[str, Any]]],
    threshold: float,
) -> Dict[str, Any]:
    """Score one candidate floor against adjudicated labels (offline, pure).

    ``labeled_cases`` carries human decisions (status + relevant_ids);
    ``retrieved_by_case`` maps case_id to recorded [{technique_id, score}]
    lists. A relevant case is *retained* when at least one relevant hit
    scores >= threshold, else it is *falsely suppressed*. A no-match case
    is *suppressed* when every score is < threshold (an empty result set
    counts as suppressed). Unresolved cases are excluded from all rates and
    reported with their max scores for sensitivity analysis. Cases missing
    from ``retrieved_by_case`` and cases with non-finite scores become
    errors: counted, never silently dropped, excluded from denominators.
    Rates are None when their denominator is zero (no evidence either way).
    """
    if isinstance(threshold, bool) or not _is_number(threshold):
        raise ThresholdError(
            f"Candidate threshold must be a finite number, got {threshold!r}"
        )
    floor = float(threshold)
    if not isinstance(labeled_cases, list) or not labeled_cases:
        raise ThresholdError("labeled_cases must be a non-empty list")
    if not isinstance(retrieved_by_case, dict):
        raise ThresholdError("retrieved_by_case must be a dict")

    labels = [_threshold_case_label(c, pos) for pos, c in enumerate(labeled_cases)]
    seen = set()
    for lab in labels:
        if lab["case_id"] in seen:
            raise ThresholdError(f"Duplicate labeled case {lab['case_id']!r}")
        seen.add(lab["case_id"])

    per_case: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []
    for lab in labels:
        case_id = lab["case_id"]
        if case_id not in retrieved_by_case:
            errors.append({"case_id": case_id, "error": "no recorded results"})
            continue
        retrieved = retrieved_by_case[case_id]
        if not isinstance(retrieved, list):
            errors.append({"case_id": case_id, "error": "retrieved results not a list"})
            continue
        if any(not isinstance(r, dict) or isinstance(r.get("score"), bool)
               or not _is_number(r.get("score")) for r in retrieved):
            errors.append({"case_id": case_id, "error": "invalid score"})
            continue
        scored = [(r.get("technique_id"), float(r.get("score"))) for r in retrieved]
        above = [s for _, s in scored if s >= floor]
        max_score = max((s for _, s in scored), default=None)
        if lab["status"] == "relevant":
            rel_scores = [s for tid, s in scored
                          if is_relevant(tid, lab["relevant_ids"])]
            max_relevant = max(rel_scores, default=None)
            outcome = "retained" if any(s >= floor for s in rel_scores) else "suppressed"
        elif lab["status"] == "no_match":
            max_relevant = None
            outcome = "suppressed" if not above else "passed-through"
        else:
            max_relevant = None
            outcome = "excluded-unresolved"
        per_case.append({
            "case_id": case_id,
            "status": lab["status"],
            "n_results": len(scored),
            "n_above": len(above),
            "max_score": max_score,
            "max_relevant_score": max_relevant,
            "outcome": outcome,
        })

    relevant = [e for e in per_case if e["status"] == "relevant"]
    nomatch = [e for e in per_case if e["status"] == "no_match"]
    unresolved = [e for e in per_case if e["status"] == "unresolved"]

    def _rate(numer: int, denom: int) -> Optional[float]:
        return (numer / denom) if denom else None

    n_retained = sum(1 for e in relevant if e["outcome"] == "retained")
    n_false_suppressed = sum(1 for e in relevant if e["outcome"] == "suppressed")
    n_nomatch_suppressed = sum(1 for e in nomatch if e["outcome"] == "suppressed")
    return {
        "threshold": floor,
        "n_labeled": len(labels),
        "n_relevant": len(relevant),
        "n_no_match": len(nomatch),
        "n_unresolved": len(unresolved),
        "n_errors": len(errors),
        "retained_relevant_rate": _rate(n_retained, len(relevant)),
        "false_suppression_rate": _rate(n_false_suppressed, len(relevant)),
        "no_match_suppression_rate": _rate(n_nomatch_suppressed, len(nomatch)),
        "n_retained_relevant": n_retained,
        "n_false_suppressed": n_false_suppressed,
        "n_no_match_suppressed": n_nomatch_suppressed,
        "unresolved_case_ids": [e["case_id"] for e in unresolved],
        "unresolved_max_scores": [
            {"case_id": e["case_id"], "max_score": e["max_score"]}
            for e in unresolved
        ],
        "errors": errors,
        "per_case": per_case,
    }


def validate_threshold_split(
    dev_ids: Any, heldout_ids: Any
) -> Dict[str, Any]:
    """Validate a dev/held-out scenario split for threshold work (offline).

    Inputs are scenario keys already normalized by the caller (e.g. plain
    case_ids — never version-qualified ``(benchmark_version, case_id)``
    pairs, since v1/v2 share 17 identical payloads and a per-record split
    would leak scenarios across the boundary). Both sets must be non-empty,
    duplicate-free, and disjoint; any overlap raises ThresholdError as a
    leakage defect. Returns the de-duplicated sorted sets with counts.
    """
    def _clean(ids: Any, what: str) -> List[str]:
        if not isinstance(ids, (list, tuple)) or not ids:
            raise ThresholdError(f"{what} must be a non-empty list of scenario ids")
        cleaned = []
        for entry in ids:
            if not isinstance(entry, str) or not entry.strip():
                raise ThresholdError(f"{what} contains an invalid scenario id {entry!r}")
            cleaned.append(entry)
        if len(set(cleaned)) != len(cleaned):
            raise ThresholdError(f"{what} contains duplicate scenario ids")
        return sorted(set(cleaned))

    dev = _clean(dev_ids, "dev_ids")
    heldout = _clean(heldout_ids, "heldout_ids")
    leaked = sorted(set(dev) & set(heldout))
    if leaked:
        raise ThresholdError(
            f"Split leaks {len(leaked)} scenario(s) across dev/held-out: {leaked[:5]}"
        )
    return {"n_dev": len(dev), "n_heldout": len(heldout),
            "dev_ids": dev, "heldout_ids": heldout}


# ---------------------------------------------------------------------------
# Baseline comparison gate (P1-14, DI-003). Compares a committed reference
# baseline against a fresh evaluation run. Pure and deterministic.
#
# Tolerance policy: BASELINE_TOLERANCE absorbs floating-point noise across
# hardware/BLAS builds only. Committed reruns are byte-identical on the same
# machine; one rank change on 15-16 evaluable cases shifts MRR by ~0.01+,
# far above tolerance. The tolerance must never be raised to mask real
# movement without a documented, separately justified reason.
# ---------------------------------------------------------------------------

BASELINE_TOLERANCE = 1e-6

#: Corpus fields that must match exactly or the comparison is invalid.
FINGERPRINT_KEYS = (
    "doc_count",
    "technique_count",
    "subtechnique_count",
    "embedding_model",
    "embedding_dim",
    "bundle_sha256",
)

#: No-match max-score shift worth flagging for human review (informational).
NO_MATCH_DELTA_NOTE = 0.05


def _is_number(value: Any) -> bool:
    import math

    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def compare_baselines(
    reference: Dict[str, Any],
    current: Dict[str, Any],
    tolerance: float = BASELINE_TOLERANCE,
) -> Dict[str, Any]:
    """Compare a fresh evaluation run against a committed reference baseline.

    Returns a report dict with compatibility verdict, per-metric rows,
    per-case rows, no-match rows, coverage, and an overall pass/fail.
    Never raises on malformed input: structural problems yield
    ``compatible: False`` with reasons instead of exceptions.
    """
    incompatibilities: List[str] = []
    failures: List[str] = []

    def _section(doc: Any) -> Dict[str, Any]:
        return doc if isinstance(doc, dict) else {}

    ref, cur = _section(reference), _section(current)

    for key in ("benchmark_version", "benchmark_sha256", "k_values",
                "metrics", "cases", "corpus"):
        if key not in ref:
            incompatibilities.append(f"reference baseline missing {key!r}")
        if key not in cur:
            incompatibilities.append(f"current run missing {key!r}")
    if incompatibilities:
        return _gate_report(False, False, incompatibilities, [], [], [], [],
                            [], {})

    if ref["benchmark_version"] != cur["benchmark_version"]:
        incompatibilities.append(
            f"benchmark version differs: {ref['benchmark_version']!r} vs "
            f"{cur['benchmark_version']!r}"
        )
    if ref["benchmark_sha256"] != cur["benchmark_sha256"]:
        incompatibilities.append("benchmark sha256 differs: stale or edited benchmark")
    if list(ref["k_values"]) != list(cur["k_values"]):
        incompatibilities.append(
            f"k_values differ: {ref['k_values']!r} vs {cur['k_values']!r}"
        )

    ref_corpus = ref["corpus"] if isinstance(ref["corpus"], dict) else {}
    cur_corpus = cur["corpus"] if isinstance(cur["corpus"], dict) else {}
    fingerprint = []
    for key in FINGERPRINT_KEYS:
        match = ref_corpus.get(key) == cur_corpus.get(key)
        fingerprint.append({"field": key, "match": bool(match)})
        if not match:
            incompatibilities.append(
                f"corpus fingerprint differs on {key!r}: "
                f"{ref_corpus.get(key)!r} vs {cur_corpus.get(key)!r}"
            )

    ref_cases = ref["cases"] if isinstance(ref["cases"], list) else None
    cur_cases = cur["cases"] if isinstance(cur["cases"], list) else None
    if ref_cases is None or cur_cases is None:
        incompatibilities.append("per-case records missing or not a list")
        ref_by_id: Dict[str, Any] = {}
        cur_by_id: Dict[str, Any] = {}
    else:
        ref_by_id = {c.get("case_id"): c for c in ref_cases if isinstance(c, dict)}
        cur_by_id = {c.get("case_id"): c for c in cur_cases if isinstance(c, dict)}
        if set(ref_by_id) != set(cur_by_id):
            incompatibilities.append(
                f"case-id sets differ: only-in-reference="
                f"{sorted(set(ref_by_id) - set(cur_by_id))} "
                f"only-in-current={sorted(set(cur_by_id) - set(ref_by_id))}"
            )

    if incompatibilities:
        return _gate_report(False, False, incompatibilities, [], [], [],
                            [], fingerprint, [])

    ref_metrics = ref["metrics"] if isinstance(ref["metrics"], dict) else {}
    cur_metrics = cur["metrics"] if isinstance(cur["metrics"], dict) else {}
    metric_rows = []
    for name in sorted(ref_metrics):
        ref_v = ref_metrics[name]
        cur_v = cur_metrics.get(name, None)
        if not _is_number(ref_v) or not _is_number(cur_v):
            incompatibilities.append(
                f"metric {name!r} missing or non-numeric; cannot compare safely"
            )
            continue
        delta = float(cur_v) - float(ref_v)
        passed = delta >= -tolerance
        metric_rows.append({
            "metric": name, "baseline": float(ref_v), "current": float(cur_v),
            "delta": delta, "pass": passed,
        })
        if not passed:
            failures.append(
                f"{name} regressed {float(ref_v):.6f} -> {float(cur_v):.6f} "
                f"(delta {delta:+.6f})"
            )
    if incompatibilities:
        return _gate_report(False, False, incompatibilities, [], [], [],
                            [], fingerprint, [])

    case_rows = []
    for case_id in sorted(ref_by_id):
        ref_rec = ref_by_id[case_id]
        cur_rec = cur_by_id[case_id]
        ref_rr = float(ref_rec.get("reciprocal_rank") or 0.0)
        cur_rr = float(cur_rec.get("reciprocal_rank") or 0.0)
        if ref_rec.get("no_match"):
            ref_scores = ref_rec.get("scores") or []
            cur_scores = cur_rec.get("scores") or []
            ref_max = max(ref_scores) if ref_scores else None
            cur_max = max(cur_scores) if cur_scores else None
            delta = (cur_max - ref_max) if ref_max is not None and cur_max is not None else None
            case_rows.append({
                "case_id": case_id, "no_match": True,
                "ref_max_score": ref_max, "cur_max_score": cur_max,
                "delta": delta,
                "note": "review manually"
                if delta is not None and abs(delta) > NO_MATCH_DELTA_NOTE
                else "stable",
            })
            continue
        had_hit = ref_rr > 1e-9
        has_hit = cur_rr > 1e-9
        outcome = "ok"
        if had_hit and not has_hit:
            outcome = "relevance-lost"
            failures.append(
                f"{case_id}: had a relevant hit in range, now has none "
                f"(reciprocal_rank {ref_rr} -> {cur_rr})"
            )
        elif abs(cur_rr - ref_rr) > 1e-9:
            outcome = "rank-shifted"
        case_rows.append({
            "case_id": case_id, "no_match": False,
            "ref_rr": ref_rr, "cur_rr": cur_rr, "outcome": outcome,
        })

    ref_cov = ref.get("coverage")
    cur_cov = cur.get("coverage")
    if _is_number(ref_cov) and _is_number(cur_cov):
        if float(cur_cov) < float(ref_cov) - tolerance:
            failures.append(
                f"coverage reduced {float(ref_cov):.4f} -> {float(cur_cov):.4f}"
            )
    ref_errs = {e.get("case_id") for e in (ref.get("errors") or [])
                if isinstance(e, dict)}
    cur_errs = {e.get("case_id") for e in (cur.get("errors") or [])
                if isinstance(e, dict)}
    new_errors = sorted(cur_errs - ref_errs)
    for case_id in new_errors:
        failures.append(f"new evaluation error on {case_id}")

    no_match_rows = [r for r in case_rows if r["no_match"]]
    return _gate_report(
        True, not failures, [], failures, metric_rows, case_rows, no_match_rows,
        fingerprint,
        [{"coverage_baseline": ref_cov, "coverage_current": cur_cov,
          "new_errors": new_errors}] if (ref_cov is not None or new_errors) else [],
    )


def _gate_report(
    compatible: bool,
    passed: bool,
    incompatibilities: List[str],
    failures: List[str],
    metric_rows: List[Dict[str, Any]],
    case_rows: List[Dict[str, Any]],
    no_match_rows: List[Dict[str, Any]],
    fingerprint: List[Dict[str, Any]],
    coverage_notes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "compatible": compatible,
        "passed": passed and compatible,
        "incompatibilities": incompatibilities,
        "failures": failures,
        "metric_rows": metric_rows,
        "case_rows": case_rows,
        "no_match_rows": no_match_rows,
        "fingerprint": fingerprint,
        "coverage_notes": coverage_notes,
    }
