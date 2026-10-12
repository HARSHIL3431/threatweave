# ThreatWeave Operations — Signals, Health Math, and Alert Readiness

How to observe RAG/LLM health today, what the numbers mean, and what is
*not* yet in place. **No alerts are active.** Anything below phrased as a
review trigger is provisional guidance, not a validated service-level
objective.

## 1. Available signals

Source: `backend/app/services/observability.py` — process-local counters
plus mean-latency accumulators, mirrored as one structured log line per
event (`ops event=<name> category=<category>`) on the existing stdout
logging pipeline. No new dependencies. No public endpoint.

| Signal (event name) | When recorded | Categories |
|---|---|---|
| `rag.query.attempted` / `rag.query.completed` | RAG query started / FAISS search returned | `ok` |
| `rag.query.failed` | Query raised | `unavailable`, `integrity`, `embedding`, `invalid_query`, `unexpected` |
| `rag.retrieval.empty` | Search returned zero hits | `ok` |
| `rag.integrity.failed` | Index/metadata failed P0-2 checks on load | `integrity` |
| `rag.unavailable.observed` | Index or metadata file missing at load | `unavailable` |
| `rag.provenance.unknown` / `rag.provenance.stale` | Status observed without / with stale `built_at` | `ok` |
| `llm.generate.completed` | Validated explanation returned | `ok` |
| `llm.generate.failed` | Generation raised | `unavailable`, `provider_error`, `timeout`, `validation`, `unexpected` |
| `llm.validation.rejected` | Validator refused output; category is the first validator error key (e.g. `ungrounded_techniques`, `confirmatory_language`) | validator key |
| `llm.explanation.degraded` | Explanation produced with no ATT&CK context | `degraded` |
| Mean latencies `rag.query`, `llm.generate` (ms) | Per successful or failed attempt (lifetime) | — |
| Rolling-window event counts (last 900 s) | Same events, in-window only; empty series omitted | same categories |
| Windowed latency stats `rag.query`, `llm.generate` | count / mean / p50 / p95 / max over in-window samples (ms) | — |

Snapshot shape: `{events, mean_latency_ms, window_seconds: 900, window_events: {name: {category: count}}, latency_ms: {name: {count, mean, p50, p95, max, unit: "ms", window_seconds}}, note}` via `get_snapshot()`. Health math via pure `build_health_report(snapshot)`, which adds `rag_failure_rate_window`, `llm_failure_rate_window` (same state rules on recency counts), and `rag_query_latency_ms_window` / `llm_generate_latency_ms_window` (values only — no latency thresholds exist, so no latency states).

## 2. Definitions and units

- **RAG failure rate** = `rag.query.failed[*]` / `rag.query.attempted[*]`.
- **LLM failure rate** = `llm.generate.failed[*]` / (`completed` + `failed`).
- **Validation rejection rate** = `llm.validation.rejected[*]` / (`completed` + `rejected`).
- **Empty-retrieval rate** = `rag.retrieval.empty` / `rag.query.completed`.
- **Degraded-explanation share** = `llm.explanation.degraded` / `llm.generate.completed`.
- **Timeout / rate-limit counts**: timeouts appear under `llm.generate.failed:timeout`; rate limits (HTTP 429) surface as `provider_error` (documented behavior, covered by test).
- **Integrity / unavailable / provenance**: absolute observation counts, not rates.
- **Latencies**: arithmetic means in milliseconds over all recorded attempts.
- **Rolling windows (P1-21, DI-015):** 900 s (15 min) recency view, counted
  on monotonic timestamps. An observation counts while its age is strictly
  below 900 s (age == window is expired). Lifetime totals are unaffected by
  expiry. Empty windows report `unknown`, never healthy: "no recent
  observations" (window empty, lifetime > 0) is distinct from "observed
  zero failures" (window non-empty, failures 0). Buffers are bounded
  (4096 timestamps per event series, 1024 latency samples per name, oldest
  dropped; floats only, no payloads). Windows start empty at process start
  and are process-local (DI-013 unchanged: no cross-worker view).
- **Latency tails (P1-21, DI-016):** units are milliseconds everywhere,
  matching the existing means. p50/p95 use linear interpolation over the
  in-window buffer (exact on the buffer, not a fleet estimate); with small
  n they are descriptive only — always read `count` first. Empty windows
  yield `null` values with `count: 0`. Non-finite or negative samples are
  ignored and uncounted (previously NaN clamped to 0.0 and counted; inf
  poisoned the mean — deliberate hardening, see phase report). Latency is
  recorded on the existing instrumentation contract (RAG times successful
  searches; LLM times all provider outcomes); failures before timing starts
  contribute no sample, consistent with prior behavior.

Every rate carries numerator, denominator, and state. **Zero denominators
yield state `unknown`** — an empty sample is never reported as a healthy 0%.
States are `unknown` (no observations), `ok` (observations, no failures),
`degraded` (any failure observed). Overall state is `degraded` if any
indicator is, `unknown` if nothing was ever observed.

## 3. Reading signals from logs (operator recipes)

```text
# RAG failures by category (last hour of collected stdout):
grep "ops event=rag.query.failed" app.log | sort | uniq -c
# LLM outcomes:
grep "ops event=llm.generate.failed" app.log | sort | uniq -c
# Validation rejections by validator key:
grep "ops event=llm.validation.rejected" app.log | sort | uniq -c
# Integrity / staleness observations:
grep -E "ops event=rag.(integrity.failed|provenance.stale)" app.log
```

In-process inspection (shell on the host, same process only):
`python -c "from app.services import observability as o; import json; print(json.dumps(o.build_health_report(o.get_snapshot()), indent=2))"`.
Note: this reflects **one process** (see §5).

## 4. Known blind spots

- Lifetime counters dilute over long uptimes (retained for trend context);
  use the 900 s window for recent behavior. The window is fixed and
  provisional — not an SLO burn-rate window.
- Multi-worker deployments keep independent copies, windows included; a
  failing worker is invisible from another worker's snapshot (DI-013).
  Process-local windows do not solve cross-worker aggregation.
- No detector-inference observability (out of scope; detector covered by
  P1-1 regression tests, not runtime metrics).
- No prompt/completion, query-text, or score logging by design (privacy).
- Lifetime means are kept for compatibility; read p50/p95/max for tails,
  always with `count`. Percentiles are buffer-descriptive, not
  statistically precise at small n, and cover one process only.

## 5. Alert-readiness policy (provisional — NOT active)

No alerting platform is configured; **no condition below notifies anyone
today**. Thresholds are provisional review triggers with rationale, not SLOs:

| Proposed review trigger | Rationale | Measurable today? | Notifies? |
|---|---|---|---|
| RAG failure rate > 5% over a deployment's lifetime counters | Above baseline noise for a local index; suggests disk/corruption issues | Yes (logs/snapshot) | No |
| Any `rag.integrity.failed` observation | Fail-closed invariant tripped; always worth investigating | Yes | No |
| LLM failure rate > 10% or any `timeout` burst | Provider/key/quota problems surface here first | Yes | No |
| Validation rejection spike after a prompt/model change | Grounding regression signal | Yes | No |
| `rag.provenance.stale` observed | Index older than 180 days serving traffic | Yes | No |

**Prerequisites for production alerts:** external log aggregation or
metrics sink, cross-process aggregation, persistence across restarts,
authenticated read path for aggregates, on-call routing. None exist.
Next step: metrics-sink export (DI-009/DI-013/DI-014), then attach the
above conditions as real alerts with burn-rate windows.

## 6. Security policy for operational details

- No public metrics endpoint exists, deliberately: the application has no
  authentication mechanism (only CORS middleware; the sole secret is the
  outbound LLM key), so any HTTP surface would be unrestricted. An
  endpoint must only be added with authentication review (DI-014).
- Aggregates contain no query text, scores, flow features, prompts,
  completions, keys, headers, exception strings, paths, or user labels.
- Health inspection never triggers retrieval, embedding, model loading,
  or LLM calls (`build_health_report` is pure).
