# Observability Windows and Latency Tails — P1-21 Phase Report (DI-015/DI-016)

No public endpoint added; no detector, retrieval, guard, threshold, label,
baseline, contract, or dependency changed.

## 1. Design (`backend/app/services/observability.py`)

- **Rolling windows (DI-015):** 900 s recency view on monotonic timestamps.
  Lifetime `_counts` semantics byte-identical; each event additionally
  appends to a per-(name, category) `deque(maxlen=4096)`. Counts while age
  strictly below the window (boundary age == window is expired). Lazy
  prune on write (touched series) + full prune on snapshot. Empty series
  omitted from `window_events`. Clock: `time.monotonic` (wall-jump immune);
  negative/odd injected times degrade to "counts as recent", never crash.
- **Latency tails (DI-016):** per-name `deque(maxlen=1024)` of
  `(timestamp, ms)`; windowed count/mean/p50/p95/max in `latency_ms`
  (units ms, matching existing means). p50/p95 by linear interpolation —
  exact on the buffer, descriptive at small n (read `count` first).
  Lifetime `[count, total]` means preserved untouched.
- **Concurrency:** one module `threading.Lock` around state mutation
  (logging outside the lock); record paths stay total (swallow-all) so
  instrumentation can never break requests. Asyncio single-loop and thread
  pools both safe; thread updates are now exact (previously possibly
  lossy — strictly stronger, verified by test).
- **Memory:** bounded by construction (4096/series, 1024/name, floats
  only — no payloads/identifiers); worst case low single-digit MB,
  realistic KBs. No DB, backend, queue, or dependency.
- **Health:** additive `rag_failure_rate_window` /
  `llm_failure_rate_window` (same unknown/ok/degraded rules; empty window
  → unknown) and value-only `*_latency_ms_window` blocks (no latency
  states — no validated thresholds exist). Overall-state scan includes the
  new rate indicators under the identical rule. Old-shape snapshots still
  validate (missing window keys → unknown/zero).

## 2. Compatibility decisions (explicit)

- Snapshot gains `window_seconds`, `window_events`, `latency_ms`;
  `test_snapshot_schema_has_no_sensitive_fields` extended for exactly these
  keys (required by the specified feature — not a weakening; banned-content
  assertions intact). All other existing tests pass unmodified.
- Deliberate input-hardening change: NaN/±inf/negative/unparseable latency
  samples are now ignored and uncounted (previously NaN clamped to 0.0 and
  counted, inf poisoned the lifetime mean). Rationale: garbage must not
  corrupt aggregates; call sites never send such values in practice.
- Thread exactness improved (lock); pre-existing loss-tolerant assertions
  still pass unchanged.

## 3. Test evidence

New `backend/tests/unit/test_observability_windows.py` (16 tests):
expiry + exact-boundary behavior, injected-clock recency, empty-window
unknown vs zero-failure ok, windowed failure detection + overall state,
lifetime survival past expiry, 4-thread × 200 exactness, deterministic
p50/p95/max (incl. interpolation value 88.0), single/empty samples,
expiry vs lifetime mean, bad-sample rejection, buffer caps, payload-free
state, reset semantics, old-snapshot compatibility. Focused suites:
42/42 pass (`test_observability_windows` + `test_observability` +
`test_ops_health`).

## 4. Unresolved limitations / owner decisions

- Window length (900 s) is provisional, not an SLO burn window; sink-side
  aggregation (DI-009) may need different windows later.
- Small-n percentiles are descriptive; no latency alert thresholds set or
  validated (provisional triggers in OPERATIONS.md unchanged, still
  non-notifying).
- Process-local only: DI-009 (sink), DI-013 (cross-worker), DI-014
  (authenticated exposure) all still open — windows change nothing there.
- RAG latency covers successful searches only; LLM covers all provider
  outcomes (pre-existing contract, preserved).
