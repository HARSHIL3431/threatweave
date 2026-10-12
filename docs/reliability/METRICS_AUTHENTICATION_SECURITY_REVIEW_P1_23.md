# Metrics Authentication Security Review (P1-23, DI-014)

Review and design only. **No endpoint implemented, no auth code written,
no behavior changed.** HEAD verified `e91ca2c`, branch `main`.

## 1. Executive conclusion

The repository has **no authentication or authorization mechanism**: no
`fastapi.security` imports, no inbound tokens/keys/sessions/roles, no
auth middleware, no rate limiting, no `TrustedHost`, no metrics config of
any kind (verified by repository-wide search). The only middleware is
CORS (browser-only, not access control); the sole secret is the outbound
`LLM_API_KEY`. Every existing route — including `/health`, `/rag/status`,
arbitrary-text `/rag/query`, `/docs`, and `/openapi.json` — is
unauthenticated by construction. Therefore **no HTTP metrics surface can
be safely supported now**: any metrics endpoint added today would be
public to whoever can reach the listener. Options A (no HTTP exposure)
and D (logs interim) from the P1-22 design are the only supportable
postures; B/C require owner-built auth, network, and secret controls that
do not exist. DI-014 stays open.

## 2. Repository evidence (confirmed implementation)

- **AuthN/AuthZ: absent.** `app/main.py:1-138` mounts CORS only
  (`main.py:66-72`); exception handlers are error-shaping, not access
  control (`main.py:76-134`). `app/dependencies.py:1-86` providers inject
  service singletons — no credential checks, no roles. No auth dependency
  exists to reuse for a metrics surface.
- **Outbound-only secret.** `Authorization: Bearer` appears exactly once,
  as an OpenAI client header (`llm_providers.py:81`) funded by
  `LLM_API_KEY` (`config.py:43`, empty default, env/`.env` loaded;
  `.env.example:27`). No validation, rotation, or scope mechanism exists;
  tests force-clear it (`conftest.py:11-20`). No inbound secret, token
  format, or identity provider exists to model metrics auth on.
- **CORS is not isolation.** Origins default to two localhost entries
  (`config.py:13`, `.env.example:5`) but CORS constrains browsers only;
  server-to-server and curl requests are unaffected. `allow_credentials`
  with wildcard methods/headers is the documented local-dev posture, not
  a boundary to rely on.
- **Network posture: inferred, not enforced.** The documented run binds
  loopback (`README:95,104`: `uvicorn app.main:app --host 127.0.0.1
  --port 8001`), but nothing in code enforces bind address, TLS,
  reverse-proxy trust, or headers (`X-Forwarded-For` is unread). Any
  deployment claim beyond loopback-default is assumption, not evidence.
- **Unauthenticated precedent.** `/health` discloses model version,
  operating point, threshold, and RAG state (`health.py:10-31`);
  `/rag/status` exposes index provenance (`rag.py:17-28`); `/rag/query`
  executes arbitrary caller-supplied text through embedding + FAISS and
  echoes the query (`rag.py:30-67`); API docs are publicly mounted
  (`main.py:59-61`). A metrics endpoint would join an already-public
  surface — it must not be assumed more private than its neighbors.
- **Snapshot sensitivity: low but non-zero.** The observability snapshot
  carries bounded names, categories, counts, and millisecond floats only —
  no query text, prompts, scores, secrets, or unbounded labels (enforced
  by construction plus `test_snapshot_contains_no_sensitive_data` and the
  schema-pinning test). What it *does* disclose is operational state:
  failure counts by category, validation-rejection keys, staleness, and
  latency distributions — useful for availability inference and
  change-detection probing (threats 2/5).

## 3. Threat model

1. **Unauthenticated external metrics access.** Impact: availability and
   health posture visible to anyone reaching the listener. Controls: none
   (no auth exists). Mitigation required: auth + network restriction
   before any route; until then, no HTTP surface.
2. **Operational-state disclosure.** Impact: model/RAG health, failure
   rates, staleness fingerprint deployment state and patch windows.
   Controls: snapshot is payload-free (limits blast radius, does not
   remove it). Mitigation: treat metrics as internal data; gate like any
   ops surface.
3. **Sensitive-payload leakage via labels/logs.** Impact: keys, prompts,
   queries in cardinality-exploding labels. Controls: closed vocabulary +
   floats-only buffers, tested. Gap: future code could add labels outside
   this discipline. Mitigation: schema-conformance test on every export
   change (closed-vocabulary assertion).
4. **Cardinality/resource exhaustion.** Impact: unbounded labels or
   scrape storms exhaust memory/CPU. Controls: bounded deques (4096/1024
   caps), no user-controlled labels today. Mitigation: keep caps;
   response-size bound; rate limiting (does not exist — owner decision).
5. **Behavior inference.** Impact: timing/error probing of an endpoint
   reveals index health and validation posture. Controls: existing
   `/rag/query` already permits richer probing — metrics add little
   *new* oracle surface, but must not exceed it. Mitigation: no per-query
   metrics, aggregates only.
6. **Process-local misread as fleet totals.** Impact: autoscaling or
   paging on single-worker numbers. Controls: `scope: process` labeling
   proposed (P1-22 §3), `note` field in snapshots. Mitigation: contract
   enforcement at export time; never relabel.
7. **Proxy/deployment bypass.** Impact: auth added in-app but stripped or
   bypassed by a misconfigured front proxy. Controls: none in repo (no
   proxy config evidenced). Mitigation: deployment requirements recorded
   as such (trusted-proxy allowlist, header discipline); app must not
   trust `X-Forwarded-*` without explicit configuration (none exists).
8. **Collection failure masking service failure.** Impact: exporter down
   read as "no failures". Controls: health unknown-on-empty semantics.
   Mitigation: pipeline-failure alerting distinct from service health;
   stale-data booleans (P1-22 §3); exporter self-counters.

No vulnerability is claimed beyond what code inspection supports; items
above are gaps against the acceptance checklist (§5), not active exploits.

## 4. Exposure options vs actual architecture

- **A. No HTTP exposure (in-process + logs).** Prerequisites: none.
  Residual risk: log-pipeline exposure (operator-owned). Supportable
  **now** — the current and recommended posture.
- **B. Internal-only authenticated endpoint.** Prerequisites: credential
  mechanism designed + reviewed, secret storage/rotation, loopback or
  network policy, closed-schema tests, rate/abuse controls, deployment
  TLS/proxy discipline. Residual risk: token sprawl, proxy bypass.
  **Not supportable now** — every prerequisite is missing.
- **C. External pull exporter.** Prerequisites: all of B plus an approved
  monitoring stack and network boundary — neither evidenced. **Not
  supportable now.**
- **D. Push export.** Prerequisites: approved receiver, sender credential
  lifecycle, delivery/backpressure policy, aggregation strategy.
  **Not supportable now.** No architecture is selected; selection is an
  owner decision.

## 5. Security acceptance checklist (testable, for any future exposure)

- [ ] Every metrics route requires verified credentials; anonymous →
  401/403 via the sanitized error envelope (no internals in bodies).
- [ ] Missing/invalid credential configuration fails closed (no
  open-by-default, no fail-open on misconfig) — tested with env absent,
  malformed, and wrong-secret cases.
- [ ] Output schema-conformance test: closed vocabulary, no query text,
  prompts, scores, secrets, raw outputs, or unbounded labels; response
  size bounded.
- [ ] `scope: process` vs `scope: aggregate` labeling enforced; unknown
  serializes field-absent + explicit, never merged with zero.
- [ ] Rate/abuse controls where justified, tested (burst + sustained).
- [ ] Health/collection failures surface as unknown/stale, never healthy.
- [ ] Deployment requirements recorded separately: bind address, TLS
  termination, trusted-proxy allowlist (no `X-Forwarded-*` trust by
  default), secret rotation procedure, log-pipeline access control.
- [ ] No token format, IdP, role model, or threshold invented here — each
  is an owner approval marked below.

## 6. Owner decisions required

Auth mechanism + credential lifecycle; network boundary + TLS/proxy
posture; option selection (A–D); rate-limit policy; retention; alert
ownership and thresholds; acceptance sign-off. None is approved by this
review.

## 7. Next step and prerequisites

Recommended: retain posture A; if exposure is ever wanted, complete the
DI-014 auth review (mechanism + rotation + tests) *before* any route
code, then implement the smallest B behind loopback with the §5
checklist green. DI-014 acceptance (documented endpoint with privacy
review and tests) additionally requires the endpoint to exist — this
document is analysis, not implementation.

## 8. Limitations and unknowns

No deployment inventory was available (bind/TLS/proxy posture beyond the
documented loopback run command is unknown); browser-only CORS was not
mistaken for a boundary; real-operator log-pipeline controls were not
assessed; threat likelihoods are unquantified without incident data.
