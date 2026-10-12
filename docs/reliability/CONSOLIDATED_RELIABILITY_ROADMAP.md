# Consolidated Reliability Roadmap — ThreatWeave (P1-13)

Evidence-based inventory of remaining work after P0-1–P0-3 and P1-1–P1-12.
Source of truth for priorities and acceptance criteria remains
`DEFERRED_IMPROVEMENTS.md` (DI-001–DI-017); this document organizes, sequences,
and separates implementable work from evidence-blocked work. No DI item is
opened, closed, or renumbered here.

Status key: evidence strength is rated **measured** (numbers from repo
artifacts), **tested** (automated suite), **documented** (reviewed prose, no
measurement), **synthetic-only** (author-made fixtures), **unverified**
(asserted without check).

## Priority distribution

No P0 items: with documented caveats, no open issue presents an immediate
integrity/safety risk that blocks reliance on current capabilities
(fail-closed validation, frozen detector, honest labeling are all tested).
P1 (5): DI-001, DI-002, DI-004, DI-006, DI-009. P2 (9): DI-005, DI-007, DI-008, DI-010, DI-012, DI-013, DI-014, DI-015, DI-017.
P3 (1): DI-016. Completed (2): DI-003, DI-011.

## Open items (P1)

### DI-001 — Expert validation of synthetic RAG benchmark — P1, evaluation, open
Justification: every retrieval metric and any future no-match policy rests on
unvalidated labels. Impact if unresolved: tuning against noise; false
regressions. Evidence: synthetic-only (17+25 cases, 42 pending review
records, 0 decisions). Prerequisites: analyst time. Implementation: adjudicate
each record (identity/date/decision/rationale), expand tactics/sub-technique
coverage. Depends on: nothing (enables DI-002, DI-012, DI-017). Acceptance:
reviewer/date provenance in fixtures; ambiguous cases re-labeled or retained.
Agent-alone: no — requires human domain judgment.
Preparation (P1-15, 2026-10-12): reviewer-ready packet
`docs/reliability/RAG_HUMAN_ADJUDICATION_GUIDE.md` (inventory verified:
v1 17, v2 25, 17 shared payloads identical, 25 unique scenarios, 42
records all pending / 0 decided); completion protocol in guide §10 and
register DI-001. DI-001 remains open — no adjudication recorded.
Decision pack (P1-26, 2026-10-12):
`docs/reliability/RAG_HUMAN_ADJUDICATION_DECISION_PACK_P1_26.md` (priority
tables with blank reviewer fields, workflow, owner decisions).
First-batch handoff (P1-29, 2026-10-12): no reviewer available, zero
decisions recorded — see
`docs/reliability/RAG_HUMAN_ADJUDICATION_BATCH_HANDOFF_P1_29.md`.
See DI-001 register entry.

### DI-002 — No-match policy — P1, accuracy, open
Justification: pipeline returns top-K unconditionally; benign flows ship with
spurious candidates. Impact: analyst noise; naive floors suppress valid hits
(misses score to 0.677). Evidence: measured (trade-off tables) on synthetic
n=9. Prerequisites: DI-001 validated benign labels. Implementation: policy +
quantified trade-offs + regression tests, only with acceptance met.
Dependencies: DI-001. Acceptance: documented policy with measured effects and
contract proof. Agent-alone: analysis yes; shipping a threshold no.

### DI-004 — Corpus freshness/refresh — P1, reliability, open
Justification: index of unknown vintage serves technique guidance.
Impact: outdated mitigations/detections. Evidence: measured (`built_at:
null`; live catalog v19.2 as of 2026-10-11; v19.x-era content present).
Prerequisites: authorization + MITRE CTI network access. Implementation:
authorized rebuild (provenance automatic), re-baseline, label re-validation.
Dependencies: none (but coordinate with DI-001). Acceptance: valid
`built_at`/age + post-rebuild baseline. Agent-alone: no (needs approval).
Authorization plan (P1-30, 2026-10-12):
`docs/reliability/MITRE_INDEX_REBUILD_AUTHORIZATION_PLAN_P1_30.md`
(BLOCKED: no target release, snapshot, or activation approval; builder
has no staging gate). DI-004 stays open. See DI-004 register entry.

### DI-006 — Remediation grounding remainder — P1, accuracy, open
Justification: plausible-but-unsupported advice is the highest per-incident
harm vector. Impact: disruptive/unsafe actions presented as grounded.
Evidence: tested (deterministic guards: CVE rule, high-impact qualification,
mitigation exemption; 18 tests) + documented gaps (invented entities,
attribution, proportionality). Prerequisites: real-LLM sample review
(opt-in). Implementation: fuzzy mitigation-constraining or unverified
labeling; human sample review. Dependencies: none for code; samples for
validation. Acceptance: check or labeling with tests + sample review.
Agent-alone: partially (code yes; validation of real output no).
Audit (P1-17, 2026-10-12): `LLM_GUARD_AND_REMEDIATION_GAP_AUDIT.md`
reproduces 8 confirmed gaps (incl. destructive-advice bypasses G-01–G-03);
production unchanged; DI-006 stays open pending sample review.
Hardening (P1-18, 2026-10-12): `LLM_GUARD_HARDENING_P1_18.md` — G-01–G-06
and G-08 bypasses now rejected by narrowed guards with regression tests.
Evaluation (P1-20, 2026-10-12): `LLM_GUARD_EVALUATION_PROTOCOL.md` —
Track A harness, 55 scored (FN 0, one known FP), 3 semantic gaps.
Track B (P1-25, 2026-10-12): `LLM_GUARD_TRACK_B_EVALUATION_P1_25.md` —
readiness BLOCKED, offline workflow prepared, zero samples.
See DI-006 register entry.

### DI-009 — Operational monitoring — P1, observability, open
Justification: silent degradation otherwise invisible. Impact: unnoticed
outages. Evidence: tested (local counters/health math) + documented (log
recipes, blind spots). Prerequisites: metrics-sink decision + auth review.
Implementation: sink export, dashboards, alerts on the three failure
classes. Dependencies: sink + auth (enables DI-013/014/015). Acceptance:
live dashboards/alerts. Agent-alone: no (infrastructure + approval).
Design (P1-22, 2026-10-12):
`docs/reliability/METRICS_EXPORT_AND_ALERT_READINESS_P1_22.md` (four
options, export contract, alert gates; nothing approved or built).
DI-009 stays open; DI-013/DI-014 keep independent criteria.
Decision pack (P1-31, 2026-10-12):
`docs/reliability/METRICS_EXPORT_ARCHITECTURE_DECISION_PACK_P1_31.md`
(evidence table, A–D matrix with rollout/rollback, contract, owner
checklist). Interim posture A; nothing approved or built.
See DI-009 register entry.

## Open items (P2)

### DI-005 — Broader detector evaluation — P2, evaluation, open
Justification: P1-8 covered all scored splits (2M records, both thresholds,
exact record match) but same-lab lineage caps generalizability claims.
Evidence: measured. Prerequisites: disjoint dataset (absent). Next: pursue
disjoint capture; drift monitoring. Agent-alone: analysis yes; new data no.

### DI-007 — Confidence calibration — P2, accuracy, open
Justification: uncalibrated labels invite over-trust, but wording guards
(P1-10/11/12) contain the harm. Evidence: tested semantics + documented.
Prerequisites: incident-level labeled correctness data. Next: calibration
study at the explanation unit. Agent-alone: no (needs data).
Remediation (P1-24, 2026-10-12):
`docs/reliability/TRUST_PRESENTATION_REMEDIATION_P1_24.md` (wording only:
lab-measured F1, score-based severity, mock labeling, similarity
qualifiers, statistical-not-probabilistic PDF). Nothing calibrated.
DI-007 stays open. See DI-007 register entry.

### DI-008 — Operator interpretation validation — P2, evaluation, open
Justification: wording is honest; reception is unmeasured. Evidence:
documented. Prerequisites: deployment + feedback loop. Agent-alone: no.
Remediation (P1-24, 2026-10-12): mock-labeling above narrows the
misreading surface; the operator study itself is still missing. DI-008
stays open. Runtime verification (P1-27, 2026-10-12): 16/16 browser
checks pass on rendered copy; reception still unmeasured.
See DI-008 register entry.

### DI-010 — Grounding-guard residuals — P2, accuracy, open
Justification: denylist/hedge/marker heuristics evadable by construction.
Evidence: documented + tested boundaries. Prerequisites: real-LLM prose set.
Next: measured FP/FN review; tighten only with numbers. Agent-alone:
partially (analysis yes; labeled set no).
Audit (P1-17, 2026-10-12): `LLM_GUARD_AND_REMEDIATION_GAP_AUDIT.md`
confirms marker/hedge/newline/separator evasions by execution with
regression-test proposals; held protections locked in by
`test_llm_guard_boundaries.py`. DI-010 stays open pending measured review.
Hardening (P1-18, 2026-10-12): `LLM_GUARD_HARDENING_P1_18.md` — positional
hedges, separator/whitespace normalization, narrowed exemptions in place
with rejection tests for every reproduced bypass.
Evaluation (P1-20, 2026-10-12): `LLM_GUARD_EVALUATION_PROTOCOL.md` —
Track A harness with versioned report; Track B unexecuted.
Track B (P1-25, 2026-10-12): readiness BLOCKED, offline workflow
prepared, zero samples.
See DI-010 register entry.

### DI-012 — Threshold drift — P2, evaluation, open
Justification: any cut-off is corpus/model-specific; silent invalidation
risk on rebuild. Evidence: measured (score magnitudes per corpus).
Prerequisites: DI-001. Next: re-derive-after-change procedure (DI-003
machinery). Agent-alone: procedure yes; validation data no.
Procedure (P1-16, 2026-10-12):
`docs/reliability/RAG_THRESHOLD_DERIVATION_PROTOCOL.md` + tested offline
helpers (`evaluate_candidate_threshold`, `validate_threshold_split`).
No threshold selected; DI-012 stays open pending DI-001 adjudication,
owner criteria, and post-change baselines. See DI-012 register entry.

### DI-013 — Multi-worker signal loss — P2, observability, open
Justification: per-worker memory loses incidents. Evidence: tested
(single-process characterization). Prerequisites: sink (DI-009).
Agent-alone: no.
Decision pack (P1-31, 2026-10-12):
`docs/reliability/METRICS_EXPORT_ARCHITECTURE_DECISION_PACK_P1_31.md` §5
(resets, restarts, duplicates, gaps, clocks, partial availability; only
push structurally aggregates). DI-013 stays open. See DI-013 register entry.

### DI-014 — Metrics export endpoint — P2, observability, open
Justification: operators need queryable aggregates. Evidence: documented
(auth blocker verified: no auth mechanism exists). Prerequisites: auth
review + API decision. Agent-alone: no (approval-gated).
Security review (P1-23, 2026-10-12):
`docs/reliability/METRICS_AUTHENTICATION_SECURITY_REVIEW_P1_23.md` —
zero auth surface confirmed (no inbound tokens/sessions/roles; all routes
including `/rag/query` unauthenticated); no metrics surface supportable
now, posture A retained. DI-014 stays open. See DI-014 register entry.
Decision pack (P1-31, 2026-10-12): threat model + mandatory gates in
`METRICS_EXPORT_ARCHITECTURE_DECISION_PACK_P1_31.md` §6; findings
re-confirmed. DI-014 stays open.

### DI-015 — Windowless counters — P2, observability, open
Justification: lifetime rates dilute outages; restarts amnesiac. Evidence:
documented. Prerequisites: sink (DI-009). Agent-alone: no.
Implementation (P1-21, 2026-10-12): process-local 900 s windows +
windowed failure-rate indicators, tested; sink/cross-worker still missing.
DI-015 stays open. See DI-015 register entry.

### DI-017 — Intent dimension — P2, evaluation, open
Justification: relevance≠malice unrepresentable in benchmark schema.
Evidence: documented (RB-016 case + T1110 definition check). Prerequisites:
DI-001 adjudication. Next: optional `intent` annotation in a future
benchmark version. Agent-alone: schema support yes; labels no.
Protocol (P1-19, 2026-10-12):
`docs/reliability/RAG_INTENT_RELEVANCE_EVALUATION_PROTOCOL.md` (four
independent dimensions, adjudication/agreement procedures, separate
metrics, DI-010/DI-006/DI-012 relations). Design only; DI-017 stays open
pending adjudication, owner decisions, and held-out evaluation.
See DI-017 register entry.

## Open items (P3)

### DI-016 — Latency tails — P3, observability, open
Justification: means hide p95/p99 trouble, but no SLO exists to violate.
Evidence: documented. Prerequisites: latency objectives. Agent-alone: yes
(bounded histogram), once objectives exist.
Implementation (P1-21, 2026-10-12): windowed count/mean/p50/p95/max in
ms over a bounded buffer, tested; no thresholds, no p99. DI-016 stays
open. See DI-016 register entry.

## Completed reference

DI-003 (retrieval comparison gate): completed (P1-14) — gate script
`scripts/check_rag_baseline.py` + 23 unit tests, GATE PASS on both
benchmark versions with zero deltas; enforcement is checklist-discipline
(no CI in repo), not automation; passing the gate controls regressions on
synthetic labels only (DI-001 stays open). See DI-003 register entry.
Preserved; revisit only on new counter-evidence.

DI-011 (non-string/empty LLM outputs → validation errors): completed with
test evidence; preserved. Revisit only on new counter-evidence.

## Recommended hardening-cycle sequence

1. DI-003 comparison gate (done, P1-14; unlocks safe retrieval work).
2. DI-001 adjudication kickoff (external, long lead — start early).
3. DI-004 authorized rebuild + re-baseline (after/overlapping DI-001 kickoff;
   re-validate labels post-rebuild).
4. DI-002 policy decision on validated labels (ship only with measured
   trade-offs) + DI-012 re-derivation + DI-017 annotations alongside.
5. DI-006 real-sample review (opt-in provider runs) → fuzzy-constrain or label.
6. DI-009 sink decision → export → DI-013/DI-015 windows → DI-014 endpoint
   (post auth review) → alerts; DI-016 tails if SLOs defined.
7. DI-007 calibration study + DI-008 operator feedback + DI-005 disjoint data
   (independent evidence tracks, any order).
8. DI-010 guard review against collected real-LLM prose throughout.

## Safe-next vs blocked-next

Safe without external prerequisites: DI-003 gate, DI-012 procedure text,
DI-010/DI-006 code analysis (not validation), roadmap/register hygiene.
Blocked on humans/data/infra/approval: DI-001, DI-002 (ship), DI-004,
DI-005 (data), DI-006 (samples), DI-007/008 (studies), DI-009/013/014/015
(sink+auth), DI-016 (objectives), DI-017 (labels).

## Phase 1 exit criteria

Engineering-exit readiness (research prototype, not production): see
`docs/reliability/PHASE_1_ENGINEERING_EXIT_CRITERIA_P1_32.md` (criterion
matrix with fresh vs prior-report evidence, ordered verification
sequence, and acceptance rules) alongside
`docs/reliability/PHASE_1_EXIT_READINESS_AUDIT_P1_28.md`. Fresh execution
(P1-33): `docs/reliability/CONTROLLED_ENGINEERING_VERIFICATION_P1_33.md`
(454 backend + 16 browser green, zero failures, hashes pinned). Final
audit (P1-34): `docs/reliability/FINAL_PHASE_1_ENGINEERING_EXIT_AUDIT_P1_34.md`
(exit APPROVED for research-prototype scope; production not established).
No DI status changes with this pointer.
