"""Lightweight operational observability for RAG/LLM degradation (P1-4, P1-5).

In-process event counters plus mean-latency accumulators, backed by the
existing stdlib logging pipeline. P1-21 adds bounded rolling-window event
views (DI-015) and windowed latency distribution statistics
(count/mean/p50/p95/max, DI-016); lifetime totals and means keep their
exact existing meanings. No new dependencies, no public endpoint,
no API contract changes. P1-5 adds pure health calculations over snapshots
and documents log-based inspection; remote export was deliberately rejected
because the application has no authentication mechanism (see
docs/reliability/OPERATIONS.md).

Privacy and safety rules:
- Event names and categories are bounded constants below. No query text,
  scores, flow fields, prompts, completions, exception strings, stack
  traces, or secrets are ever recorded or logged here. Window buffers and
  latency samples retain floats (timestamps, milliseconds) only — never
  payloads or identifiers.
- Every public function swallows its own failures: instrumentation can
  never break detection or explanation requests.
- Counters are process-local and reset on restart. They are NOT durable
  fleet-wide metrics; multi-worker deployments keep independent copies
  (see DI-013). A metrics-export endpoint is an explicit non-goal of this
  phase (see DI-009).
- Rolling windows are recency views, not cluster visibility: "no recent
  observations" (empty window) is reported as unknown, never as healthy.
"""

from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple
import threading
import time

from app.core.logging import get_logger

logger = get_logger("ops")

# Bounded event vocabulary. Do not add high-cardinality labels.
RAG_QUERY_ATTEMPTED = "rag.query.attempted"
RAG_QUERY_COMPLETED = "rag.query.completed"
RAG_QUERY_FAILED = "rag.query.failed"
RAG_RETRIEVAL_EMPTY = "rag.retrieval.empty"
RAG_INTEGRITY_FAILED = "rag.integrity.failed"
RAG_UNAVAILABLE_OBSERVED = "rag.unavailable.observed"
RAG_PROVENANCE_UNKNOWN = "rag.provenance.unknown"
RAG_PROVENANCE_STALE = "rag.provenance.stale"
LLM_GENERATE_COMPLETED = "llm.generate.completed"
LLM_GENERATE_FAILED = "llm.generate.failed"
LLM_VALIDATION_REJECTED = "llm.validation.rejected"
LLM_EXPLANATION_DEGRADED = "llm.explanation.degraded"

# Bounded failure categories (never exception strings).
CATEGORY_OK = "ok"
CATEGORY_UNAVAILABLE = "unavailable"
CATEGORY_INTEGRITY = "integrity"
CATEGORY_EMBEDDING = "embedding"
CATEGORY_INVALID_QUERY = "invalid_query"
CATEGORY_PROVIDER_ERROR = "provider_error"
CATEGORY_TIMEOUT = "timeout"
CATEGORY_VALIDATION = "validation"
CATEGORY_UNEXPECTED = "unexpected"
CATEGORY_DEGRADED = "degraded"

_counts: Dict[str, Dict[str, int]] = {}
_latency_ms: Dict[str, list] = {}  # name -> [count, total_ms] (lifetime)

# Rolling-window state (P1-21, DI-015/DI-016). All process-local, bounded,
# payload-free. Timestamps are monotonic seconds (immune to wall-clock
# jumps); latency samples are (timestamp, milliseconds) pairs.
WINDOW_SECONDS = 900  # 15-minute recency view (provisional, see OPERATIONS.md)
WINDOW_SERIES_MAXLEN = 4096  # cap per event series; oldest dropped first
LATENCY_SAMPLE_MAXLEN = 1024  # cap per latency name; oldest dropped first

_window_events: Dict[str, Dict[str, Deque[float]]] = {}
_latency_samples: Dict[str, Deque[Tuple[float, float]]] = {}
_lock = threading.Lock()


def _now() -> float:
    """Injectable monotonic clock (tests pass explicit timestamps)."""
    return time.monotonic()


def _prune_series(series: Deque[float], cutoff: float) -> None:
    while series and series[0] <= cutoff:
        series.popleft()


def _prune_latency(samples: Deque[Tuple[float, float]], cutoff: float) -> None:
    while samples and samples[0][0] <= cutoff:
        samples.popleft()


def _prune_all(now: float) -> None:
    cutoff = now - WINDOW_SECONDS
    for cats in _window_events.values():
        for series in cats.values():
            _prune_series(series, cutoff)
    for samples in _latency_samples.values():
        _prune_latency(samples, cutoff)


def record_event(name: str, category: str = CATEGORY_OK,
                 now: Optional[float] = None) -> None:
    """Increment a bounded event counter and emit one structured log line.

    Lifetime totals keep their existing meaning; the timestamp additionally
    feeds the rolling window. ``now`` accepts an injected monotonic
    timestamp (tests); callers omit it.
    """
    try:
        stamp = _now() if now is None else float(now)
        with _lock:
            bucket = _counts.setdefault(name, {})
            bucket[category] = bucket.get(category, 0) + 1
            series = _window_events.setdefault(name, {}).setdefault(
                category, deque(maxlen=WINDOW_SERIES_MAXLEN))
            series.append(stamp)
            _prune_series(series, stamp - WINDOW_SECONDS)
        logger.info(f"ops event={name} category={category}")
    except Exception:
        pass


def record_latency(name: str, milliseconds: float,
                   now: Optional[float] = None) -> None:
    """Accumulate a latency sample: lifetime mean plus windowed distribution.

    Units are milliseconds everywhere. Non-finite or negative inputs are
    ignored (clamped): a bad sample must not corrupt aggregates. ``now``
    accepts an injected monotonic timestamp (tests); callers omit it.
    """
    try:
        value = float(milliseconds)
        if not (value >= 0.0) or value != value or value == float("inf"):
            return
        stamp = _now() if now is None else float(now)
        with _lock:
            entry = _latency_ms.setdefault(name, [0, 0.0])
            entry[0] += 1
            entry[1] += value
            samples = _latency_samples.setdefault(
                name, deque(maxlen=LATENCY_SAMPLE_MAXLEN))
            samples.append((stamp, value))
            _prune_latency(samples, stamp - WINDOW_SECONDS)
    except Exception:
        pass


def _percentile(sorted_values: List[float], pct: float) -> Optional[float]:
    """Linear-interpolation percentile (exact on the buffer, not an estimate
    of fleet behavior). Returns None on empty input; small-n results are
    descriptive only (see OPERATIONS.md)."""
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(rank)
    frac = rank - low
    high = min(low + 1, len(sorted_values) - 1)
    return float(sorted_values[low] + frac * (sorted_values[high] - sorted_values[low]))


def _latency_window_stats(samples: Deque[Tuple[float, float]]) -> Dict[str, Any]:
    values = sorted(v for _, v in samples)
    if not values:
        return {"count": 0, "mean": None, "p50": None, "p95": None,
                "max": None, "unit": "ms", "window_seconds": WINDOW_SECONDS}
    return {
        "count": len(values),
        "mean": sum(values) / len(values),
        "p50": _percentile(values, 50),
        "p95": _percentile(values, 95),
        "max": float(values[-1]),
        "unit": "ms",
        "window_seconds": WINDOW_SECONDS,
    }


def get_snapshot() -> Dict[str, Any]:
    """Return process-local counts, means, and rolling-window views (JSON-safe).

    Adds ``window_seconds``, ``window_events`` (in-window counts; empty
    series omitted), and ``latency_ms`` (windowed count/mean/p50/p95/max)
    alongside the unchanged ``events`` lifetime totals and
    ``mean_latency_ms`` lifetime means. Pruning makes repeated reads
    content-identical under a fixed clock.
    """
    try:
        with _lock:
            _prune_all(_now())
            window_events = {
                name: {cat: len(series) for cat, series in cats.items() if len(series)}
                for name, cats in _window_events.items()
            }
            window_events = {k: v for k, v in window_events.items() if v}
            latency_window = {
                name: _latency_window_stats(samples)
                for name, samples in _latency_samples.items()
                if len(samples)
            }
            snapshot = {
                "events": {name: dict(cats) for name, cats in _counts.items()},
                "mean_latency_ms": {
                    name: (total / count if count else 0.0)
                    for name, (count, total) in _latency_ms.items()
                },
                "window_seconds": WINDOW_SECONDS,
                "window_events": window_events,
                "latency_ms": latency_window,
                "note": ("process-local counters; reset on restart; not fleet-wide; "
                         "window_* and latency_ms cover the recent "
                         f"{WINDOW_SECONDS}s recency view only"),
            }
        return snapshot
    except Exception:
        return {"events": {}, "mean_latency_ms": {}}


def reset() -> None:
    """Clear all counters, windows, and latency buffers (tests and restarts)."""
    try:
        with _lock:
            _counts.clear()
            _latency_ms.clear()
            _window_events.clear()
            _latency_samples.clear()
    except Exception:
        pass


def category_for_error_code(error_code: Optional[str]) -> str:
    """Map established LLM error codes to bounded observability categories."""
    mapping = {
        "LLM_UNAVAILABLE": CATEGORY_UNAVAILABLE,
        "LLM_PROVIDER_ERROR": CATEGORY_PROVIDER_ERROR,
        "LLM_TIMEOUT": CATEGORY_TIMEOUT,
        "LLM_VALIDATION_ERROR": CATEGORY_VALIDATION,
    }
    return mapping.get(str(error_code or ""), CATEGORY_UNEXPECTED)


# ---------------------------------------------------------------------------
# Health calculations (P1-5). Pure functions over a snapshot dict: no I/O,
# no model loading, no retrieval, no LLM calls. States distinguish "unknown"
# (no observations) from "ok" (observations, no failures) from "degraded"
# (failures observed). No alert thresholds live here: any review triggers
# are provisional policy documented in docs/reliability/OPERATIONS.md, not
# validated service-level objectives.
# ---------------------------------------------------------------------------

STATE_UNKNOWN = "unknown"
STATE_OK = "ok"
STATE_DEGRADED = "degraded"


def _count(events: Dict[str, Any], name: str, category: Optional[str] = None) -> int:
    bucket = events.get(name, {})
    if not isinstance(bucket, dict):
        return 0
    if category is None:
        return sum(v for v in bucket.values() if isinstance(v, int))
    value = bucket.get(category, 0)
    return value if isinstance(value, int) else 0


def _rate(failures: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return failures / total


def _state(total: int, failures: int) -> str:
    if total <= 0:
        return STATE_UNKNOWN
    return STATE_DEGRADED if failures > 0 else STATE_OK


def build_health_report(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Compute defensible health indicators from a snapshot dict.

    Every indicator carries numerator, denominator, and state. Zero
    denominators yield state "unknown" — an empty sample is never reported
    as a healthy 0% failure rate. Pure and deterministic.
    """
    try:
        events = snapshot.get("events", {})
        latencies = snapshot.get("mean_latency_ms", {})
        window_events = snapshot.get("window_events", {})
        latency_windows = snapshot.get("latency_ms", {})
        if not isinstance(events, dict):
            events = {}
        if not isinstance(latencies, dict):
            latencies = {}
        if not isinstance(window_events, dict):
            window_events = {}
        if not isinstance(latency_windows, dict):
            latency_windows = {}
    except Exception:
        return {"indicators": {}, "state": STATE_UNKNOWN}

    attempted = _count(events, RAG_QUERY_ATTEMPTED)
    rag_failed = _count(events, RAG_QUERY_FAILED)
    rag_completed = _count(events, RAG_QUERY_COMPLETED)
    rag_empty = _count(events, RAG_RETRIEVAL_EMPTY)
    integrity = _count(events, RAG_INTEGRITY_FAILED)
    unavailable = _count(events, RAG_UNAVAILABLE_OBSERVED)
    prov_unknown = _count(events, RAG_PROVENANCE_UNKNOWN)
    prov_stale = _count(events, RAG_PROVENANCE_STALE)

    llm_completed = _count(events, LLM_GENERATE_COMPLETED)
    llm_failed = _count(events, LLM_GENERATE_FAILED)
    validation_rejected = _count(events, LLM_VALIDATION_REJECTED)
    degraded = _count(events, LLM_EXPLANATION_DEGRADED)

    llm_attempts = llm_completed + llm_failed
    validation_total = llm_completed + validation_rejected

    def latency(name: str) -> Optional[float]:
        value = latencies.get(name)
        return float(value) if isinstance(value, (int, float)) else None

    def window_latency(name: str) -> Dict[str, Any]:
        block = latency_windows.get(name)
        if not isinstance(block, dict):
            return {"count": 0, "mean": None, "p50": None, "p95": None,
                    "max": None, "unit": "ms"}
        out = {
            "count": block.get("count", 0),
            "mean": block.get("mean"),
            "p50": block.get("p50"),
            "p95": block.get("p95"),
            "max": block.get("max"),
            "unit": "ms",
        }
        if not isinstance(out["count"], int):
            out["count"] = 0
        return out

    # Windowed rates reuse lifetime state rules on recency counts: an empty
    # window is "unknown" (no recent observations), never healthy-by-default,
    # so "observed zero failures recently" stays distinguishable from
    # "nothing observed recently". No alert thresholds are set here.
    w_attempted = _count(window_events, RAG_QUERY_ATTEMPTED)
    w_rag_failed = _count(window_events, RAG_QUERY_FAILED)
    w_llm_completed = _count(window_events, LLM_GENERATE_COMPLETED)
    w_llm_failed = _count(window_events, LLM_GENERATE_FAILED)
    w_llm_attempts = w_llm_completed + w_llm_failed

    indicators: Dict[str, Any] = {
        "rag_failure_rate": {
            "failures": rag_failed, "attempts": attempted,
            "rate": _rate(rag_failed, attempted),
            "state": _state(attempted, rag_failed),
        },
        "rag_empty_rate": {
            "empty": rag_empty, "completed": rag_completed,
            "rate": _rate(rag_empty, rag_completed),
            "state": _state(rag_completed, rag_empty),
        },
        "rag_integrity_failures": {
            "count": integrity,
            "state": STATE_UNKNOWN if attempted + integrity == 0
            else (STATE_DEGRADED if integrity > 0 else STATE_OK),
        },
        "rag_unavailable_observations": {"count": unavailable},
        "rag_provenance_unknown": {"count": prov_unknown},
        "rag_provenance_stale": {
            "count": prov_stale,
            "state": STATE_DEGRADED if prov_stale > 0 else STATE_UNKNOWN
            if prov_unknown + prov_stale == 0 else STATE_OK,
        },
        "llm_failure_rate": {
            "failures": llm_failed, "attempts": llm_attempts,
            "rate": _rate(llm_failed, llm_attempts),
            "state": _state(llm_attempts, llm_failed),
        },
        "llm_validation_rejection_rate": {
            "rejected": validation_rejected, "evaluated": validation_total,
            "rate": _rate(validation_rejected, validation_total),
            "state": _state(validation_total, validation_rejected),
        },
        "llm_degraded_share": {
            "degraded": degraded, "completed": llm_completed,
            "rate": _rate(degraded, llm_completed),
            "state": _state(llm_completed, degraded),
        },
        "rag_query_latency_ms_mean": {"value": latency("rag.query")},
        "llm_generate_latency_ms_mean": {"value": latency("llm.generate")},
        "rag_failure_rate_window": {
            "failures": w_rag_failed, "attempts": w_attempted,
            "rate": _rate(w_rag_failed, w_attempted),
            "state": _state(w_attempted, w_rag_failed),
            "window_seconds": WINDOW_SECONDS,
        },
        "llm_failure_rate_window": {
            "failures": w_llm_failed, "attempts": w_llm_attempts,
            "rate": _rate(w_llm_failed, w_llm_attempts),
            "state": _state(w_llm_attempts, w_llm_failed),
            "window_seconds": WINDOW_SECONDS,
        },
        "rag_query_latency_ms_window": window_latency("rag.query"),
        "llm_generate_latency_ms_window": window_latency("llm.generate"),
    }
    try:
        observed = sum(
            value
            for bucket in events.values()
            if isinstance(bucket, dict)
            for value in bucket.values()
            if isinstance(value, int)
        )
        if observed <= 0:
            overall = STATE_UNKNOWN
        else:
            overall = STATE_OK
            for indicator in indicators.values():
                if isinstance(indicator, dict) and indicator.get("state") == STATE_DEGRADED:
                    overall = STATE_DEGRADED
                    break
    except Exception:
        overall = STATE_UNKNOWN
    return {"indicators": indicators, "state": overall}
