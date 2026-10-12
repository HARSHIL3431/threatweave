# Metrics Export and Alert-Readiness Design (P1-22, DI-009)

Architecture analysis and documentation only. **No sink, endpoint, alert
delivery, or cross-worker aggregation is implemented here**, and selecting
an option below does not authorize building it.

## 1. Current capabilities and gaps (from repo evidence)

- **Produced:** lifetime counters + means (`events`, `mean_latency_ms`),
  900 s process-local rolling windows (`window_events`,
  `window_seconds: 900`), windowed latency count/mean/p50/p95/max in ms
  (`latency_ms`), and pure health math with unknown/ok/degraded states —
  all in `backend/app/services/observability.py`, tested, payload-free.
- **Consumed:** stdout structured logs (`ops event=…`) scraped by hand;
  same-process shell inspection. The snapshot is **not** exposed through
  any API (verified: no metrics route; `/rag/status` reports index
  readiness/provenance only).
- **Health triggers** in OPERATIONS.md §5 are provisional review guidance,
  not SLOs; nothing notifies anyone.
- **Gaps:** no export, no persistence across restarts, no cross-worker
  aggregation (DI-013), no authenticated read path (DI-014), no latency
  SLOs (DI-016), no alert delivery or ownership. Deployment evidence is a
  single-process `uvicorn app.main:app` run (backend README); no
  monitoring stack, reverse proxy, or credential store exists in-repo —
  none is invented below. The sole secret is the outbound `LLM_API_KEY`
  (env-injected, never logged).

## 2. Export architectures compared

### Option A — Authenticated internal-only metrics endpoint

Read-only route (e.g. `/ops/metrics`) returning the snapshot schema,
bound to loopback or cluster-internal listener, gated by a bearer token
from env. Assessment: auth = shared-secret header (no identity layer
exists to integrate); exposure = minimal if loopback-bound, risky the
moment it binds wider; secrets = one read token alongside `LLM_API_KEY`
handling; labels = already bounded, no cardinality risk; complexity = low
(code + auth review + tests); failure = endpoint failure must never affect
detection (read-only snapshot copy); freshness = scrape-driven, seconds;
multi-worker = still per-process without an aggregator (does not solve
DI-013); persistence = none; self-observability = export errors countable
in-process. Blocker: **authentication review first** (DI-014) — even a
token gate needs storage, rotation, and a no-logging rule.

### Option B — Pull-based exporter for an existing monitoring stack

Prometheus-style text exposition consumed by an operator-run scraper.
Assessment: identical auth/exposure posture to A (scraper needs the same
credential); adds exposition-format mapping (counters vs gauges for
windows/percentiles; `unknown` has no Prometheus native — export as
absent series + `*_stale` boolean); complexity = medium (format + docs +
scraper config the repo does not own); freshness = scrape interval;
aggregation/persistence/history = delegated to the stack — **which does
not exist in this repository's evidence**, so B is conditional on an
external stack decision. No stack is assumed here.

### Option C — Push-based export to an approved backend

Process pushes snapshots on an interval to an approved receiver.
Assessment: auth = sender credential + TLS to a known endpoint; network =
egress-only (attractive where ingress is forbidden); backpressure =
bounded local queue, drop-oldest with a dropped counter, never block
requests; freshness = push interval; multi-worker = receiver-side
aggregation possible (the only option that structurally enables DI-013);
persistence/history = receiver-side; complexity = highest (retry, clock,
drop policy, receiver contract); self-observability = export
success/failure/lag counters required. Blockers: receiver selection,
credential management, and retention policy — all owner decisions.

### Option D — Structured logs / periodic snapshots (interim)

Keep stdout JSON lines (already emitted per event) plus an optional
periodic full-snapshot log line; aggregation deferred to whatever log
pipeline the operator already has. Assessment: auth = whatever protects
the logs (nothing new exposed); complexity ≈ zero new code; freshness =
log latency; multi-worker = mergeable by (host, pid, time) **if** a
collector exists; persistence/history = log retention; failure = local
disk pressure (bounded by log rotation, operator-owned). Limits: no
queryable aggregates in-repo, windows recomputed downstream, latency
percentiles must be re-derived from raw samples the logs do not carry
(log per-event lines exist; per-sample latency values are not logged —
by privacy design, so tail recomputation downstream is approximate).

**Evidence-supported reading:** D works today with zero new surface and
is the only option needing no new decision except log retention; A is the
smallest code step but is blocked on DI-014 auth review; C is the only
structural answer to DI-013 but needs the most owner decisions (receiver,
credentials, retention); B is moot without an external stack. No option
is owner-approved — §6 lists the gates.

## 3. Safe export contract (v0 proposal, implementation-neutral)

- **Names/definitions:** today's snapshot keys verbatim (`events.*`,
  `mean_latency_ms.*`, `window_events.*`, `latency_ms.{count,mean,p50,
  p95,max}`); any rename is a major schema version.
- **Units/windows:** milliseconds; `window_seconds: 900` explicit on every
  payload; lifetime vs window never mixed in one field.
- **Identity/aggregation:** every payload carries `process: {pid,
  started_at_monotonic_origin, host: <operator-supplied>}`; per-process
  values are labeled `scope: process`. Future aggregates use
  `scope: aggregate` with `sources: [process…]`, `aggregation: sum|...`,
  and window alignment rules — **never relabel process-local counters as
  global**.
- **Time/freshness:** exporter timestamps with wall clock at scrape/push
  time plus `snapshot_monotonic_age`; consumers treat data older than N×
  interval as stale (stale-data boolean, not silent gaps).
- **Unknown/unavailable/zero:** `unknown` (no observations) serializes as
  field-absent + explicit `unknown: true`; zero observed failures
  serialize as explicit `0` — the two must never merge downstream.
- **Dimensions/labels:** closed vocabulary only (today's event/category
  names); no query text, prompts, identifiers, secrets, scores, or raw
  outputs — enforced by reusing the in-process snapshot object, never a
  parallel collection path.
- **Evolution:** additive fields minor; renames/removals major with dual
  publish during migration. Exporter errors surface as their own bounded
  counters, never as metric values.

## 4. Alert readiness (decisions before any alert)

- **Candidate signals:** windowed RAG/LLM failure rates, integrity-failure
  observations, validation-rejection spikes, provenance-stale, p95/latency
  movement (descriptive; thresholds unvalidated).
- **Volume/warm-up:** minimum window observations before evaluation (else
  `unknown` suppresses); cold-start and post-restart windows must not
  page.
- **Semantics:** alert on windowed rates, trend lifetime separately; burn
  windows are SLO-derived when SLOs exist (they do not).
- **Trade-offs:** explicit FP cost (noise, toil) vs FN cost (silent
  degradation) per signal, owner-signed.
- **Ops hygiene:** dedup keys, cooldowns, recovery/resolve conditions,
  runbook pointer per alert; missing/stale exports and exporter failure
  alert **on the pipeline**, never interpreted as healthy.
- **Ownership/response:** named owner + expected response per alert —
  absent today. **No threshold below is validated; no delivery is
  configured; nothing here pages anyone.**

## 5. Dependencies and decision gates

- **DI-015/DI-016 (this repo state):** window + tail primitives exist
  process-locally — evidence-ready, no decision needed to *measure*.
- **DI-014 (auth review):** gate for Options A/B. Decidable from repo
  evidence that none exists; the review itself is an owner/security
  decision.
- **DI-013 (multi-worker):** only Option C structurally aggregates;
  A/B/D need a separate aggregation story. Independent criteria stand.
- **DI-009 (this design):** closes only on implemented + validated
  approved path with safeguards (rotation, retention, stale handling,
  pipeline alerting) — not on this document.
- Owner decisions required: option selection, receiver/stack, credentials
  + rotation, retention, window/SLO approval, alert ownership, acceptance
  thresholds. Repository evidence answers none of these; it only bounds
  what is safe to propose.
