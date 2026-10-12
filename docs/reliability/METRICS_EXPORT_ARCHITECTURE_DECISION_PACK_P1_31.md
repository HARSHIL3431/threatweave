# Metrics Export Architecture Decision Pack (P1-31: DI-009, DI-013, DI-014)

Documentation and read-only analysis. **No endpoint, exporter, sink,
auth, alert, or aggregation implemented; no option approved.** Builds on
the P1-21 implementation, P1-22 option analysis, and P1-23 security
review — new here are the consolidated evidence table, A–D comparison
with rollout/rollback detail, the versioned contract, aggregation and
threat analysis, alert inventory, and the owner checklist.

## 1. Executive summary and safe interim recommendation

Keep the current posture: process-local snapshots + structured stdout
logs, no new HTTP routes (Option A). It needs no new decisions, exposes
nothing, and preserves the tested P1-21 semantics. Long-term, only a
push-based design (Option C) structurally answers cross-worker
aggregation (DI-013), but it requires the most owner decisions
(receiver, credentials, retention); an authenticated endpoint (Option B)
is the smallest code step yet is blocked on the DI-014 auth review that
found zero auth surface; pull (Option D) is moot without an external
stack. Recommendation ≠ approval: every path beyond A awaits explicit
owner sign-off.

## 2. Current-state evidence table (verified 2026-10-12)

| Fact | Evidence (file/symbol) | Strength |
|---|---|---|
| 900 s rolling windows, per-(event,category) deques maxlen 4096 | `observability.py`: `WINDOW_SECONDS = 900`, `WINDOW_SERIES_MAXLEN`, `_window_events` | code (measured) |
| Latency count/mean/p50/p95/max (ms), 1024-sample buffers | `observability.py`: `LATENCY_SAMPLE_MAXLEN`, `_latency_window_stats` | code (measured) |
| Lifetime totals/means retained unchanged | `observability.py`: `_counts`, `_latency_ms`; prior suites green | code + tested |
| Module lock; record paths total/swallow-all | `observability.py`: `_lock`, try/except recorders | code + tested |
| No metrics route; no authN/Z, rate limiting, TrustedHost, metrics config | repo-wide search: zero hits; only CORS middleware (`main.py:66-72`) | code (measured absence) |
| Snapshot payload-free, closed vocabulary | construction + `test_snapshot_contains_no_sensitive_data`, schema pin | code + tested |
| Single-process uvicorn run documented; no stack/proxy/credential store | backend README run command; `.env.example` (only outbound `LLM_API_KEY`) | docs (deployment default, not enforcement) |
| Health triggers provisional, non-notifying | `OPERATIONS.md` §5 | docs |

## 3. Architecture comparison (A–D)

| Dimension | A: in-process + logs (interim, supportable now) | B: authenticated endpoint/exporter | C: push to approved collector | D: pull by external stack |
|---|---|---|---|---|
| Infra/deps | none | auth mechanism + review + tests | receiver, sender creds, retention | monitoring stack (absent) |
| AuthN/Z | n/a (no surface) | credential design + storage/rotation + tests (all missing) | sender cred + TLS to known endpoint | scraper credential (same gap as B) |
| Exposure/threat | log-pipeline only (operator-owned) | new HTTP attack surface; proxy-bypass risk (no proxy config evidenced) | egress-only (attractive); forged-push risk → receiver auth + dedup | ingress scrape; unauthenticated scrape = public metrics |
| Aggregation | none (per-process, honestly labeled) | still per-process without aggregator | receiver-side aggregation possible (only structural DI-013 answer) | stack-side aggregation possible (stack absent) |
| Sink-down behavior | n/a | endpoint failure must not affect detection (read-only copy) | bounded drop-oldest queue + dropped counter; never block requests | missed scrapes = gaps (stale-data booleans required) |
| Sensitivity | closed labels already; log retention is the boundary | same + token handling | same + sender-credential handling | same + scrape-ACL handling |
| Complexity/cost | ~zero | low code, high review cost | highest (retry, clock, drop policy, contract) | medium + external stack cost |
| Validation work | existing suites | auth tests (anon/role/malformed/misconfig), schema tests, load test | + delivery/drop/replay tests | + exposition-format + scraper-config tests |
| Rollback | n/a | remove route / gate flag | stop pushes, revoke credential | remove exposition / scrape job |
| Owner decisions | log retention only | mechanism, rotation, bind/TLS/proxy, rate policy | receiver, creds, retention, aggregation rules | stack selection, network boundary |

## 4. Minimum export contract (v0, implementation-neutral)

Snapshot keys verbatim; milliseconds; `window_seconds: 900` on every
payload; `process: {pid, started_monotonic, host}` + `scope: process`
required; future aggregates use `scope: aggregate` with sources, method,
and window-alignment — never relabel process values. Exporter wall-clock
timestamp + `snapshot_monotonic_age`; older than N×interval ⇒ stale
boolean. `unknown` ⇒ field-absent + explicit flag (never merged with
zero). Closed vocabulary only — reuse the snapshot object, never a
parallel path (this is the enforcement mechanism). Additive fields
minor; renames major with dual-publish. Exporter health as bounded
self-counters. Health derivation reuses current unknown/ok/degraded rules
unchanged. Retention/access/audit: owner-defined; defaults deny.

## 5. DI-013 aggregation analysis

Process-local metrics understate multi-worker fleets (a failing worker is
invisible elsewhere) and overstate if summed naively across restarts
(counters reset; windows drain). Trusted-collector aggregation must
handle: resets (process-identity epochs), restarts (cold windows ⇒
unknown, not zero), duplicate/redelivered pushes (idempotent windows or
dedup keys), missing samples (explicit gaps, never interpolation),
clock differences (monotonic ages + exporter wall timestamps; no
cross-host arithmetic on monotonic values), partial availability (quorum
notes, never silent extrapolation). Push (C) carries these answers;
endpoint/pull needs a separate aggregation story. Deployment facts needed:
worker count/topology, shared nothing confirmed, collector selection.
No shared storage or distributed code is implemented here.

## 6. DI-014 threat model and mandatory gates

Threats: anonymous reads; ops-state disclosure (failure counts, rejection
keys, staleness, latency shapes); cardinality/DoS via labels or scrape
storms; forged/replayed pushes; credential theft/lifecycle gaps;
internal-network fallacies (CORS is browser-only; loopback run-command is
unenforced default); unaudited access; docs/OpenAPI advertising the
surface. P1-23 claims re-confirmed against current code (zero auth
surface; all routes including `/rag/query` unauthenticated). Gates before
any activation: verified credentials on every route; fail-closed on
missing/invalid config; schema-conformance + size bounds; scope labeling;
rate/abuse controls; unknown-not-healthy collection semantics; recorded
deployment requirements (bind, TLS, trusted-proxy allowlist with no
`X-Forwarded-*` trust by default, rotation, log-pipeline ACLs). No token
format, IdP, roles, or thresholds invented.

## 7. Alert-readiness inventory (no approved thresholds)

Measurable today: windowed/lifetime failure, rejection, empty, degraded
rates with unknown semantics; integrity/stale observations; latency
count/mean/p50/p95/max. Provisional indicators: OPERATIONS.md §5 review
triggers (explicitly non-notifying). Candidate alerts (each needs
rationale + volume/warm-up + FP/FN trade-off + dedup/cooldown/recovery +
pipeline-failure alerting + owner + runbook): RAG failure-rate breach,
integrity observation, LLM failure/timeout burst, post-change validation
spike, provenance-stale, p95 movement. Approved SLOs/thresholds: none
exist. p95 describes tails; it establishes no SLO by itself.

## 8. Owner decision checklist

Export option; receiver/stack; credential mechanism + rotation; network
boundary + TLS/proxy posture; retention; aggregation rules; window/SLO
approval; per-alert rationale, thresholds, ownership, runbooks;
acceptance sign-off. Repository evidence answers none; it bounds what is
safe to propose.

## 9. Proposed implementation and rollout (not authorized)

A→(auth review)→B-loopback-gated or C-pilot with contract §4: build
behind flag, checklist §6 green, dual-publish on schema change, staged
rollout per worker with health verification, rollback = flag off /
credential revoke / route removal. Each stage needs its own sign-off.

## 10. Failure handling, rollback, acceptance

Sink down: degrade to posture A (logs), pipeline-failure alert fires,
never healthy-by-default. Rollback restores prior pair/config and
re-verifies status. Acceptance per item: DI-009 dashboards/alerts live
with safeguards; DI-013 aggregated cross-process visibility or enforced
single-process constraint; DI-014 documented endpoint + privacy review +
tests. Design documents satisfy none of these.

## 11. Dependency map

DI-015/016 primitives feed all options (no new instrumentation needed
for A; B/C/D reuse the snapshot object). DI-009 decides option+receiver;
DI-013 needs C or a separate aggregation story; DI-014 gates any HTTP
surface. DI-001/002/004/005/006/007/008/010/012/017 proceed
independently of metrics choices.

## 12. Open questions and evidence to close them

Receiver/stack existence (owner inventory); credential lifecycle design
(security review); worker topology (deployment survey); SLO values
(owner + data); alert ownership (org decision); retention policy (owner).
Each closes with a named artifact + sign-off, never with inference.
