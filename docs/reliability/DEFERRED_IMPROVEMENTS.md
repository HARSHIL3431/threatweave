# Deferred Improvements Register — ThreatWeave Reliability

Living register for known limitations that are out of scope for the current
phase or blocked on external input. An item is marked `completed` only when
its acceptance criteria are met and supported by actual verification. Test
coverage alone never closes an item.

Companion: `CONSOLIDATED_RELIABILITY_ROADMAP.md` (P1-13) organizes these
items by category, priority, evidence strength, and execution sequence. This
register remains the source of truth for IDs, statuses, and acceptance.

Conventions: IDs are stable (`DI-NNN`). Priorities P0–P3. Status is one of
`open`, `planned`, `blocked`, `completed`. Related work: `TASKS.md` tracks
phase completion; this file tracks residual risk and debt.

---

## DI-001 — Expert validation and expansion of the synthetic P1-2 RAG benchmark

- **Priority:** P1. **Category:** evaluation. **Status:** open.
- **Limitation and evidence:** `backend/tests/fixtures/rag_benchmark_v1.json`
  holds 17 synthetic cases whose labels are author-curated, not
  expert-validated (declared in-file). P1-4 added `rag_benchmark_v2.json`
  (25 cases: v1 preserved byte-identically plus gray-zone RB-016/017 and
  benign probes RB-N03..N08), but the new labels are equally synthetic.
  P1-6 audited every case against corpus definitions and recorded baselines
  (`docs/reliability/RAG_BENCHMARK_LABEL_AUDIT.md`): most labels are
  directly supported with misses attributable to retrieval, but RB-014
  (T1070 vs retrieved T1685.005 near-equivalent) needs genuine taxonomy
  expertise, and RB-016 tests relevance-without-malice. Adjudication queue
  `backend/tests/fixtures/rag_label_review_v1.json` holds 42 records
  (17 v1 + 25 v2), **all pending, zero human decisions recorded**.
- **Proposed improvement:** independent security-analyst review of every
  expected-ID set; expand to cover more tactics and sub-technique-heavy
  queries; record reviewer identity and date in the fixture.
- **Dependencies:** analyst time. **Risk if unresolved:** tuning retrieval
  against noisy labels.
- **Acceptance:** fixture carries reviewer/date provenance; ambiguous cases
  re-labeled or explicitly retained. Audit artifacts and validator coverage
  alone do not close this item: closure requires recorded analyst
  adjudication with identity, date, decision, and rationale per case.
  P1-7 prepared a source-cited evidence packet
  (`docs/reliability/RAG_ATTACK_EVIDENCE_REVIEW.md`, accessed 2026-10-11):
  5 live official technique/version pages plus local corpus definitions
  cover all 25 cases at evidence-prepared status (RB-014 taxonomy question
  and RB-016 intent framing documented with open questions). Human
  adjudication recorded: still 0 of 42 review records.
- **Preparation completed (P1-15, 2026-10-12, no adjudication performed):**
  reviewer-ready packet published as
  `docs/reliability/RAG_HUMAN_ADJUDICATION_GUIDE.md` (four-dimension review
  method, decision protocol mapped to the current queue schema, per-case
  worklist for all 25 unique scenarios / 42 records with verbatim queries,
  priority order with reviewer questions, and a DI-001 completion protocol
  in its §10). Verified inventory: v1 17 cases (15 match + 2 no-match),
  v2 25 cases (16 match + 9 no-match), 17 shared payloads byte-identical,
  25 unique scenarios, queue 42 records all pending / 0 decided, baselines
  untouched and not rerun. Smallest additive queue extension proposed
  (optional `reviewer.qualification`, `reviewer.evidence_refs`,
  `reviewer.decided_ids`/`decided_no_match`) — documented in the guide,
  NOT implemented pending project-owner approval. No benchmark label,
  baseline, retrieval ranking, or threshold changed; no review decision
  fabricated.
- **Still outstanding (DI-001 stays open):** recorded human adjudication
  with identity, date, decision, and rationale for all 42 records;
  ATT&CK-qualified resolution of RB-014 (and any cross-tactic `revise`);
  RB-016 relevance-vs-malice ratification; reviewer-count/qualification
  mix (project-owner decision); approval sign-off; versioned adjudicated
  benchmark + new baselines without overwriting references.
- **Decision pack (P1-26, 2026-10-12, no adjudication performed):**
  `docs/reliability/RAG_HUMAN_ADJUDICATION_DECISION_PACK_P1_26.md` —
  reconciled inventory (17/25/17-shared/25-unique/42-records verified,
  zero inconsistencies), 13-scenario priority tables with exact queries,
  retrieval, evidence, alternatives, and blank reviewer fields, plus
  workflow, owner decisions, and post-review actions. DI-001 stays open.
- **First-batch handoff (P1-29, 2026-10-12, no reviewer available):**
  `docs/reliability/RAG_HUMAN_ADJUDICATION_BATCH_HANDOFF_P1_29.md` —
  RB-014/016/017 exact questions, expertise/channel/sign-off requirements,
  and field-level completion instructions. Zero decisions recorded; queue
  byte-unchanged (42 pending). DI-001 stays open.
- **Proposed improvement:** independent security-analyst review of every
  expected-ID set; expand to cover more tactics and sub-technique-heavy
  queries; record reviewer identity and date in the fixture.
- **Dependencies:** analyst time. **Risk if unresolved:** tuning retrieval
  against noisy labels.
- **Acceptance:** fixture carries reviewer/date provenance; ambiguous cases
  re-labeled or explicitly retained.

## DI-002 — Benign-query false positives and relevance/no-match policy

- **Priority:** P1. **Category:** accuracy. **Status:** open.
- **Limitation and evidence:** the pipeline has no relevance threshold:
  baseline v1 shows no-match queries RB-N01/RB-N02 always return 5 results
  (max scores 0.221/0.252). P1-4 measured the trade-off on recorded v1
  results: misses score as high as 0.648–0.677 (RB-001/009/014), so any
  floor that preserves hits cannot separate no-match from high-score
  misses, and the no-match sample (n=2, now n=9 in benchmark v2) is far too
  small to validate a production cut-off. Pure policy helpers
  (`apply_score_floor`, `apply_score_margin`, `evaluate_policy` in
  `app/services/rag_evaluation.py`) exist for offline comparison only and
  are deliberately NOT wired into production retrieval.
- **Proposed improvement:** define a principled policy (score floor,
  margin rule, or explicit no-match verdict) with measured precision/recall
  trade-offs on an expanded benign set.
- **Dependencies:** DI-001 (validated benign labels). **Risk:** benign flows
  presented alongside spurious ATT&CK candidates; conversely, a naive floor
  silently suppresses valid candidates without a measured reason.
- **Acceptance:** documented policy + threshold (or explicit no-threshold
  rationale) + regression tests on benign cases. A threshold may ship only
  with quantified recall/no-match effects and contract-compatibility proof;
  until then production retrieval stays unchanged by policy. P1-6 label
  audit found no definitively-wrong label requiring policy re-baselining,
  but confirmed the ambiguity set (RB-001/006/009 multi-label, RB-016 gray
  zone) that any future policy must handle explicitly.

## DI-003 — Retrieval quality limitations and fingerprint comparison risk

- **Priority:** P1. **Category:** evaluation. **Status:** completed.
- **Limitation and evidence:** baseline `rag_baseline_v1.json`: P@5 0.253,
  R@5 0.600, MRR@5 0.536 on synthetic labels; 5/15 evaluable cases score
  zero. A v2 baseline (`rag_baseline_v2.json`, 25 cases) is recorded by
  P1-4 without touching v1 history. Baselines are only comparable across
  identical index/model fingerprints (records pin corpus counts, model id,
  benchmark sha256).
- **Implementation (P1-14):** comparison gate
  (`app/services/rag_evaluation.py:compare_baselines`, runner
  `scripts/check_rag_baseline.py`; bare command checks v1,
  `--benchmark .../rag_benchmark_v2.json` checks v2). Enforces benchmark
  version/sha, K values, case-id sets, and all six corpus fingerprint
  fields before comparing; fails on metric drops beyond 1e-6 float-noise
  tolerance, per-case complete relevance loss, coverage reduction, and new
  errors; reports rank shifts and no-match deltas without failing on them.
  Exit codes 0 pass / 1 regression / 2 invalid. Fresh runs default to temp
  files and can never overwrite references (path guard). Covered by
  `backend/tests/unit/test_baseline_gate.py` (23 tests). Verified live:
  GATE PASS on both versions with zero deltas, all fingerprints match,
  coverage 1.0, reference files byte-untouched.
- **What "completed" does not mean:** no CI exists in this repository, so
  enforcement is a documented developer-run checklist step, not automation;
  a passing gate controls regressions on synthetic labels only and proves
  nothing about real-world retrieval correctness (DI-001 stays open).
- **Acceptance met:** enforced comparison step with fingerprint equality,
  per the checklist-step branch of the acceptance criteria.

## DI-004 — ATT&CK corpus freshness unknown until authorized rebuild

- **Priority:** P1. **Category:** reliability. **Status:** open.
- **Limitation and evidence:** production index predates P0-1 provenance;
  `/rag/status` reports `built_at: null`, age `unknown`. P1-3 surfaces this
  honestly in prompts but cannot fix the underlying staleness. P1-7
  established external context only: the live catalog is currently v19.2
  (2026-04-28–current, per official version history, accessed 2026-10-11),
  and the corpus demonstrably contains v19.x-era content (T1685.005,
  created 2026-04-14) — a suggestive but unverified recency hint, NOT a
  release mapping. The production index has not been refreshed.
- **Proposed improvement:** authorized rebuild via
  `scripts/build_mitre_index.py` (persists provenance automatically), then
  re-run the P1-2 baseline to detect corpus-shift effects.
- **Dependencies:** authorization to rebuild; network access to MITRE CTI.
  **Risk:** outdated technique guidance presented as current.
- **Acceptance:** status shows valid `built_at`/age; baseline re-recorded
  post-rebuild.
- **Authorization plan (P1-30, 2026-10-12, read-only, NOT authorized):**
  `docs/reliability/MITRE_INDEX_REBUILD_AUTHORIZATION_PLAN_P1_30.md`.
  Evidence: moving `master` source URL with no hash check; on-disk bundle
  47.9 MB / 858 patterns vs 697 indexed; production provenance absent
  (`built_at: null`); builder writes production paths directly with no
  staging gate; pair-swap activation + fail-closed loader proposed.
  All checklist items unresolved; no download, rebuild, or approval
  occurred. DI-004 stays open.

## DI-005 — Broader detector evaluation

- **Priority:** P2. **Category:** evaluation. **Status:** open.
- **Limitation and evidence:** P1-8 evaluated all 7 scored splits
  (2,017,986 records) at both frozen thresholds
  (`docs/reliability/DETECTOR_EVALUATION_REPORT.md`,
  `data/processed/analysis/detector_eval_p18/`): test-only pooled OP-A
  F1 0.6264 / OP-B F1 0.5858, reproducing the experiment record exactly.
  Classification: Tuesday descriptive (selection-touched), 6 test days
  honest holdout wrt selection, same-lab caveats throughout — descriptive
  evidence, not independent generalization. Known gaps: Monday train
  unscored (in-sample by construction); infiltration n=36; PortScan
  nearly invisible to OP-A (R=0.008); DDoS-day benign FPR 0.42–0.50;
  ROC-AUC misleading under imbalance (Thu-Afternoon 0.93 vs PR-AUC 0.003).
- **Proposed improvement:** independent capture evaluation with disjoint
  collection lineage; per-family calibration research (not implementation);
  drift monitoring across days.
- **Dependencies:** disjoint dataset (absent). **Risk:** undetected
  day- or family-specific drift; live-traffic overconfidence.
- **Acceptance:** a genuinely independent evaluation (no shared
  preprocessing/selection lineage) with per-family metrics. Metrics
  calculated here do not close this item.

## DI-006 — Grounding for unsupported factual claims and remediation text

- **Priority:** P1. **Category:** accuracy. **Status:** open.
- **Limitation and evidence:** P1-3 validates technique IDs/names and scans
  prose for smuggled IDs and confirmatory language, but free-text
  `recommended_actions` and factual assertions (e.g. invented ports, CVE
  numbers, remediation steps) have no allowlist to check against —
  `recommended_actions` in the mock provider derive from retrieved
  mitigations, but real-LLM prose cannot be deterministically verified.
  P1-9 confirmed the concrete failure modes with synthetic fixtures
  (`remediation_grounding_cases_v1.json`, 15 cases): invented hosts/accounts
  (`invented_host_and_account`), unqualified disruptive actions
  (`high_impact_unqualified`, `evidence_destroying_advice`,
  `service_disrupting_block`), and smuggled IDs in actions all validate
  cleanly under pre-P1-9 rules.
- **Safeguards implemented (deterministic):** `unsupported_factual_claim`
  rejects any `CVE-YYYY-NNNN` mention (no CVE data exists anywhere in the
  pipeline); `unqualified_high_impact_action` rejects non-mitigation-
  grounded actions matching high-impact verb patterns without explicit
  qualification markers; actions quoting retrieved mitigations pass as
  authoritative STIX guidance. Rubric:
  `docs/reliability/REMEDIATION_GROUNDING_RUBRIC.md`. Covered by
  `test_remediation_grounding.py` (18 tests) plus endpoint rejection test.
- **Audit completed (P1-17, 2026-10-12, read-only, no production change):**
  `docs/reliability/LLM_GUARD_AND_REMEDIATION_GAP_AUDIT.md` reproduces 8
  confirmed weaknesses with synthetic probes (G-01 marker gaming, G-02
  mitigation-substring/template exemption smuggling, G-03 disruptive
  synonyms such as reset-at-scale/offline/suspend/reboot/lock-out passing
  unqualified, G-04 hedge-word injection, G-05 CVE separator variants,
  G-06 T-ID separator obfuscation, G-07 invented actors/ports/root causes,
  G-08 newline-split multi-word confirmatory terms) plus 4 likely items
  needing tests (L-01 exemption breadth vs shortest mitigation, L-02
  abbreviation sentence-splitting, L-03 duplicate-JSON-keys note, L-04
  real-model frequency unknown) and the permanent lexical-vs-semantic
  boundary. Held protections re-verified (malformed/None, standard IDs,
  same-line confirmatory, ASCII CVEs, listed verbs, unallowed-ID template,
  502 mapping, secret-free details) and locked in by
  `backend/tests/unit/test_llm_guard_boundaries.py` (8 tests).
  Production behavior left exactly as found for every finding.
- **Remaining validation requirements:** owner-reviewed pattern/marker
  tightening with regression tests (G-01–G-06, G-08 proposals in audit
  §3); real-LLM sample review (opt-in) for semantic truth,
  proportionality, and bypass frequency (G-07, H-01/H-02); any
  unverified-labeling contract change with tests.
- **Recommended next step:** span-aware mitigation exemption +
  position-aware qualification markers + extended verb patterns (audit §8
  order), then real-sample review. DI-006 stays open.
- **Hardening implemented (P1-18, 2026-10-12):**
  `docs/reliability/LLM_GUARD_HARDENING_P1_18.md`. Clause-scoped markers
  with adjacent-conditional exception, span-redacted mitigation exemption,
  six narrow verb patterns (reset-at-scale/offline/suspend/reboot/lock-out/
  deactivate), negation/quotation handling, positional hedges,
  whitespace-collapsed confirmatory scan, broadened CVE separators, T-ID
  separator normalization. All P1-17 bypasses G-01–G-06/G-08 now rejected;
  full pre-existing suite passes unmodified. G-07 semantic limits remain.
  DI-006 stays open pending sample review + labeling decision.
- **Evaluation framework (P1-20, 2026-10-12, measurement only):**
  `backend/app/services/guard_evaluation.py` + versioned fixture
  `backend/tests/fixtures/llm_guard_eval_v1.json` (57 synthetic cases) +
  runner `scripts/eval_guard_harness.py` + report
  `reports/llm_guard_eval/guard_eval_report_v1.json` + protocol
  `docs/reliability/LLM_GUARD_EVALUATION_PROTOCOL.md`. Track A results:
  55 scored (TP 35, FN 0, TN 19, FP 1 — the known CF-09 honest FP),
  unsafe-acceptance 0.0, benign-rejection 0.05, 0 errored, 2 unassessable,
  3 semantic gaps (SG-01–03: lexically-correct accepts of unsupported
  content). Track B (real-model review) unexecuted. Production guards
  unchanged. DI-006 stays open.
- **Track B readiness (P1-25, 2026-10-12, no live calls):**
  `docs/reliability/LLM_GUARD_TRACK_B_EVALUATION_P1_25.md`. Readiness
  BLOCKED: no explicit live-run authorization, opt-in flags unset (a
  `.env` key entry exists but was never read/used and authorizes
  nothing). Workflow prepared instead: Track B manifest (4 approved
  synthetic inputs, annotations pending), offline measure path with
  secret-refusal in `backend/app/services/guard_track_b.py` +
  `scripts/eval_guard_track_b.py` (no network code by design), 11 tests.
  Zero Track B samples, zero confusion counts; Track A/B never pooled.
  DI-006 stays open.
- **Documentation-only (no reliable string check):** invented entities
  without trigger patterns (`invented_root_cause_gap` passes by design and
  says so), malware-family/actor attribution by name, invented port/service
  facts, proportionality judgments, whether a qualified action is wise.
- **Proposed improvement (remaining):** constrain recommendations to retrieved
  mitigations/detection guidance with fuzzy-match validation, or label
  model-generated advice as unverified in the response contract.
- **Dependencies:** none. **Risk:** plausible-but-unsupported remediation
  presented as grounded.
- **Acceptance:** deterministic check or explicit unverified labeling with
  tests. The checks above narrow but do not eliminate the risk, so this
  item stays open pending human review of real-LLM remediation samples.

## DI-007 — Calibration of future risk/confidence output

- **Priority:** P2. **Category:** accuracy. **Status:** open.
- **Limitation and evidence:** mock confidence derives from cosine-score
  cutoffs (0.55/0.45) and real-LLM confidence is model-asserted; neither is
  calibrated. The anomaly score is not a probability of attack.
  P1-10 audited every exposed value
  (`docs/reliability/CONFIDENCE_RISK_SEMANTICS_AUDIT.md`): confirmed that
  `risk_score` is byte-identical to `anomaly_score` under a placeholder
  note (now pinned by test + OpenAPI descriptions), that severity mixes
  absolute magnitude bands with threshold-relative decision bands, that
  technique confidence is a similarity band or free assertion (never a
  probability), and that family blindness (P1-8: OP-A PortScan recall
  0.008) limits what any band can mean. Misleading-adjacent wording
  recorded: mock-preview "High likelihood", landing "risk-based severity",
  Gauge 0–1 dial, PDF "probabilistic" disclaimer nuance — none changed
  pending approved wording work.
- **Proposed improvement:** calibrate any future confidence at the actual
  decision unit (per-explanation correctness), never by reusing retrieval
  scores or anomaly scores as probabilities.
- **Dependencies:** labeled explanation-correctness data. **Risk:**
  over-trust in uncalibrated confidence labels.
- **Acceptance:** calibration measured and documented, or confidence
  withheld in favor of qualitative language. Audit documentation alone
  does not close this item.
  P1-11 wording fixes (server PDF "Anomaly Score (Uncalibrated)" label,
  Gauge "(uncalibrated)" caption, landing score/severity copy, mock
  likelihood removal): reduce misreading opportunities; they do not
  calibrate anything and leave this item open.
  P1-12 display reliability: Gauge out-of-range/invalid handling made
  explicit ("dial capped" caption, "n/a" safe state, raw value preserved),
  PDF label/value regression-tested; score bounds still unproven and
  calibration still absent — item stays open.
- **Presentation remediation (P1-24, 2026-10-12, wording only):**
  `docs/reliability/TRUST_PRESENTATION_REMEDIATION_P1_24.md`. Landing
  "F1-validated" → "Lab-measured F1", "Risk-based severity" →
  "Score-based", mock-preview mock-labeled, `ConfidenceBadge` tooltip +
  sample-PDF similarity qualifiers, backend PDF "probabilistic" →
  "statistical" and "Candidate confidence" header; full `next build`
  green. No calibration performed or claimed. Runtime verification
  (P1-27): 16/16 browser checks confirm rendered wording only.
  DI-007 stays open pending
  the calibration study; DI-008 stays open pending the operator study.

## DI-008 — Real-world validation of anomaly-vs-intrusion distinction

- **Priority:** P2. **Category:** evaluation. **Status:** open.
- **Limitation and evidence:** prompts, disclaimers, and validators enforce
  candidate framing, but no labeled live-traffic study confirms operators
  interpret outputs that way.
- **Dependencies:** operational deployment + analyst feedback loop.
- **Risk:** correct wording still misread as attribution under pressure.
- **Acceptance:** operator study or incident-review feedback recorded.
  (P1-11 candidate-framing and placeholder-calibration copy improvements
  support, but do not substitute for, this validation — item stays open.)
  P1-12 adds explicit capped-dial/uncalibrated captions operators can see,
  without providing the study above.
- **Presentation remediation (P1-24, 2026-10-12):** mock-preview
  mock-labeling and similarity-qualifier changes above (shared with
  DI-007); the operator study itself is still missing. DI-008 stays open.
- **Runtime verification (P1-27, 2026-10-12):**
  `docs/reliability/TRUST_PRESENTATION_RUNTIME_VERIFICATION_P1_27.md` —
  first Playwright suite (8 tests × light + dark-narrow projects, 16/16
  pass) verifies rendered wording, SAMPLE banners, tooltips, candidate
  framing, and sample-PDF bytes; live detect/RAG spot-checked functional.
  Reception still unmeasured. DI-008 stays open.

## DI-009 — Operational monitoring for provider/retrieval degradation

- **Priority:** P1. **Category:** observability. **Status:** open.
- **Limitation and evidence:** P1-4 added process-local signals in
  `app/services/observability.py`, wired into `RagService.query`,
  `_load_store`, `status`, and `LLMService.generate_explanation`: RAG
  attempted/completed/failed (unavailable/integrity/embedding/invalid),
  empty retrieval, integrity failures, provenance unknown/stale
  observations, LLM completed/failed (unavailable/provider/timeout/
  validation/unexpected), validation rejections by error key, degraded
  explanations, and mean latencies for RAG queries and LLM generation.
  P1-5 added pure health calculations (`build_health_report`: per-indicator
  numerator/denominator/state, unknown-on-empty semantics) and
  `docs/reliability/OPERATIONS.md` (signal table, definitions, log recipes,
  blind spots, provisional review triggers).
  What remains absent: any export endpoint, dashboard, alerting, or
  cross-process aggregation — `get_snapshot()` is in-process only, and no
  alert is active.
- **Proposed improvement:** metrics-sink export (e.g. Prometheus-style
  endpoint with non-sensitive aggregates) plus alerts on failure-rate and
  latency thresholds.
- **Dependencies:** metrics sink decision; authentication review for any
  HTTP surface (no auth mechanism exists today — see OPERATIONS.md §6).
  **Risk:** silent degradation of explanation availability/quality.
- **Acceptance:** dashboards/alerts covering the three failure classes.
  Logs/counters alone do not close this item.
- **Design completed (P1-22, 2026-10-12, documentation only):**
  `docs/reliability/METRICS_EXPORT_AND_ALERT_READINESS_P1_22.md` —
  inventory of current capabilities (lifetime + 900 s windows + tails,
  log/shell consumption, provisional triggers), four-option comparison
  with per-option auth/exposure/secret/complexity/failure/freshness/
  aggregation/persistence analysis grounded in repo evidence (no invented
  stack, credentials, or services), versioned export contract (units,
  windows, process identity, unknown-vs-zero, closed labels, evolution),
  and alert-readiness gates (volume/warm-up, dedup/cooldown/recovery,
  pipeline-failure alerting, ownership). No endpoint, sink, aggregation,
  or delivery implemented.
- **Unresolved owner decisions:** option selection; receiver/stack;
  credentials + rotation; retention; window/SLO approval; alert ownership
  and acceptance thresholds. **Security prerequisites:** DI-014 auth
  review before any HTTP surface; closed-label enforcement via snapshot
  reuse; stale-data handling.
- **Implementation + validation requirements (for closure):** approved
  path built with safeguards, pipeline-failure alerting, documented
  retention, and tests — then dashboards/alerts per acceptance.
  DI-009 stays open; DI-013/DI-014 keep independent criteria.
- **Decision pack (P1-31, 2026-10-12, documentation only):**
  `docs/reliability/METRICS_EXPORT_ARCHITECTURE_DECISION_PACK_P1_31.md`
  (evidence table, A–D matrix with rollout/rollback, versioned contract,
  aggregation + threat analysis, alert inventory, owner checklist).
  Interim posture A; nothing approved or built. DI-009 stays open.

## DI-010 — Confirmatory-language guard residual risk

- **Priority:** P2. **Category:** accuracy. **Status:** open.
- **Limitation and evidence:** added in P1-3 (`llm_validation.py`):
  sentence-scoped denylist with negation/hedge guard. Adversarial or
  convoluted phrasing ("no doubt this is confirmed") can evade it, and
  over-broad terms could false-positive on legitimate prose.
- **Proposed improvement:** review validator rejections on real-LLM traffic
  samples; tighten terms or add lightweight assertion-scope parsing only
  with measured precision/recall.
- **Dependencies:** real-LLM sample outputs (opt-in). **Risk:** confirmed-
  attack framing slipping into validated output.
- **Acceptance:** measured false-positive/negative rates on a labeled prose
  set. P1-9 extends the same pattern to high-impact verbs and qualification
  markers (`unqualified_high_impact_action`): identical evasion properties
  apply — e.g. prefacing any action with "consider" satisfies the marker
  check by construction — so marker coverage must be reviewed against
  real-LLM samples, not assumed complete.
- **Audit completed (P1-17, 2026-10-12, read-only, no production change):**
  `docs/reliability/LLM_GUARD_AND_REMEDIATION_GAP_AUDIT.md` confirms by
  execution that marker gaming (G-01), hedge-word injection (G-04),
  newline-split multi-word terms (G-08), CVE/ID separator variants
  (G-05/G-06), and position-independent matching are reproducible, with
  per-finding regression-test proposals and smallest safe remediations
  (position-aware markers/hedges, whitespace/dash normalization, span-aware
  exemption). Held protections locked in by
  `backend/tests/unit/test_llm_guard_boundaries.py`.
- **Remaining validation requirements:** measured FP/FN rates on a labeled
  prose set (acceptance, still unmet); real-LLM prose for L-01/L-02 and
  bypass-frequency measurement; owner review of any pattern tightening.
- **Recommended next step:** position-aware hedge/marker checks +
  normalization (audit §8 order), then measured review. DI-010 stays open.
- **Hardening implemented (P1-18, 2026-10-12):**
  `docs/reliability/LLM_GUARD_HARDENING_P1_18.md`. Positional hedges,
  separator/whitespace normalization, and the G-01–G-03 verb/exemption
  tightening above; every reproduced bypass now has a rejection test.
  DI-010 stays open pending measured FP/FN rates on real-model prose.
- **Evaluation framework (P1-20, 2026-10-12, measurement only):** Track A
  synthetic harness above (55 scored: FN 0, FP 1 known; 3 semantic gaps;
  report versioned under `reports/llm_guard_eval/`). Track B unexecuted.
  Production guards unchanged. DI-010 stays open.
- **Track B readiness (P1-25, 2026-10-12, no live calls):** readiness
  BLOCKED (no authorization, opt-ins unset); offline manifest + measure
  workflow with secret-refusal prepared (`guard_track_b.py`,
  `eval_guard_track_b.py`, Track B manifest, 11 tests); zero samples.
  See `LLM_GUARD_TRACK_B_EVALUATION_P1_25.md`. DI-010 stays open.

## DI-011 — Non-string and empty LLM outputs handled as validation errors

- **Priority:** P1. **Category:** reliability. **Status:** completed.
- **Limitation and evidence:** pre-P1-3, a provider returning `None`
  crashed validation with `AttributeError` instead of the controlled
  `LLM_VALIDATION_ERROR` (found by P1-3 test).
- **Improvement made:** `validate_llm_output` rejects non-string input with
  `LLM_VALIDATION_ERROR`; covered by `test_none_output_rejected`,
  `test_empty_string_output_rejected`, `test_non_object_json_rejected` in
  `backend/tests/unit/test_explanation_grounding.py`.
- **Acceptance met:** full backend suite green (see P1-3 report).

## DI-012 — Threshold drift across index or embedding-model changes

- **Priority:** P2. **Category:** evaluation. **Status:** open.
- **Limitation and evidence:** P1-4 policy analysis shows score magnitudes
  are corpus- and model-specific (v1 no-match maxima 0.221/0.252; v2 benign
  AV text RB-017 reaches 0.434). P1-6 adds direct evidence: misses score up
  to 0.677 (RB-014) and near-equivalent rivals (T1685.005) outrank credited
  labels, so any cut-off tuned today is fragile to both corpus content and
  label scope. Any future index rebuild or model swap shifts the entire
  score distribution, silently invalidating any tuned cut-off and historical
  baseline comparisons.
- **Proposed improvement:** re-run `scripts/eval_rag_benchmark.py` on both
  benchmark versions after any corpus/model change; re-derive (never carry
  over) any future threshold; gate on fingerprint match before comparing.
- **Dependencies:** DI-001. **Risk:** stale thresholds suppressing valid
  candidates or passing noise after a rebuild.
- **Acceptance:** post-change baselines recorded with matching fingerprints
  before any policy decision.
- **Procedure completed (P1-16, 2026-10-12, no threshold selected):**
  reproducible derivation protocol published as
  `docs/reliability/RAG_THRESHOLD_DERIVATION_PROTOCOL.md` (verified score
  semantics: L2-normalized embeddings both sides, IndexFlatIP inner
  product = cosine similarity, 6-decimal stored scores, `>=` comparison
  convention, unconditional top-K, fail-closed failure representations,
  relevance-vs-malice separation; adjudicated-label requirements with
  unresolved exclusion + sensitivity bounds; scenario-level dev/held-out
  split with leakage prevention; fixed-denominator metrics with empty-set
  rules; owner-predeclared selection rule with "insufficient evidence" as
  the default outcome; experiment metadata pinning reusing the DI-003 gate;
  promotion/rollback checklist). Pure offline helpers tested:
  `evaluate_candidate_threshold` + `validate_threshold_split` in
  `app/services/rag_evaluation.py`, covered by
  `backend/tests/unit/test_threshold_derivation.py`. Existing
  `apply_score_floor`/`apply_score_margin`/`evaluate_policy` reused as-is.
- **Still outstanding (DI-012 stays open):** DI-001 adjudication (0 of 42
  decided — threshold work cannot begin); owner-predeclared acceptable
  recall/suppression criteria and cost rationale; minimum held-out size;
  post-rebuild baselines with matching fingerprints; independent held-out
  evaluation; production-change approval.
- **Explicit confirmation:** no production score floor or margin added;
  retrieval ranking, top-K behavior, API contract, FAISS index, benchmark
  labels, and saved baselines unchanged; no candidate threshold presented
  as production-ready.

## DI-013 — Operational signal loss in multi-worker deployments

- **Priority:** P2. **Category:** observability. **Status:** open.
- **Limitation and evidence:** `app/services/observability.py` counters are
  process-local by design (`get_snapshot()` carries an explicit non-goal
  note); uvicorn workers, restarts, and redeploys each keep independent,
  ephemeral copies. Covered by unit tests only within a single process
  (asyncio-exact; threads characterized as never-corrupt but possibly
  lossy, per `test_thread_race_never_corrupts_state`).
- **Proposed improvement:** external sink export (counter push or scrape
  endpoint with non-sensitive aggregates) as the DI-009 follow-up.
- **Dependencies:** metrics sink decision (shared with DI-009). **Risk:**
  production incidents visible in only one worker's memory, then lost.
- **Acceptance:** aggregated cross-process visibility or documented
  single-process deployment constraint.
- **Decision-pack pointer (P1-31, 2026-10-12):** aggregation analysis
  (resets, restarts, duplicates, gaps, clocks, partial availability) in
  `METRICS_EXPORT_ARCHITECTURE_DECISION_PACK_P1_31.md` §5; only push (C)
  structurally aggregates. DI-013 stays open.

## DI-014 — No metrics export endpoint yet

- **Priority:** P2. **Category:** observability. **Status:** open.
- **Limitation and evidence:** P1-4 deliberately added no public endpoint
  (sensitive-implementation exposure risk); signals are observable via logs
  and in-process `get_snapshot()` only. Verified by
  `backend/tests/unit/test_observability.py` (15 tests); no endpoint, API,
  or response-contract changes were made. P1-5 re-verified the blocker:
  the application has no authentication mechanism (only CORS middleware;
  sole secret is the outbound LLM key), so any HTTP metrics surface would
  be unrestricted. Decision recorded in OPERATIONS.md §6: no endpoint until
  authentication review. Local inspection path (logs + snapshot + health
  math + recipes) is the sanctioned alternative.
- **Proposed improvement:** read-only ops endpoint exposing aggregate
  counts/means without query text, scores, or secrets; include in API
  contract documentation when added.
- **Dependencies:** API review for the new surface. **Risk:** operators
  cannot query signals without log access or a shell.
- **Acceptance:** documented endpoint with privacy review and tests.
- **Security review (P1-23, 2026-10-12, analysis only, no code):**
  `docs/reliability/METRICS_AUTHENTICATION_SECURITY_REVIEW_P1_23.md`.
  Finding: no authentication/authorization mechanism exists anywhere
  (no `fastapi.security` usage, no inbound tokens/sessions/roles, CORS-only
  middleware, outbound-only `LLM_API_KEY`); all current routes including
  `/health`, `/rag/status`, and arbitrary-text `/rag/query` are
  unauthenticated, so no metrics surface is supportable now — posture A
  (no HTTP exposure) retained. Threat model (8 items), option comparison,
  testable acceptance checklist, and owner-decision list included.
  No endpoint, auth code, exporter, or behavior changed.
  DI-014 stays open; DI-009/DI-013 keep independent criteria.
- **Decision-pack pointer (P1-31, 2026-10-12):** threat model +
  mandatory gates in `METRICS_EXPORT_ARCHITECTURE_DECISION_PACK_P1_31.md`
  §6; P1-23 zero-auth-surface finding re-confirmed. DI-014 stays open.

## DI-015 — Lifetime counters have no time window

- **Priority:** P2. **Category:** observability. **Status:** open.
- **Limitation and evidence:** observability counters accumulate since
  process start and never reset; failure rates therefore dilute over long
  uptimes (a recent outage hides inside months of healthy history) and
  reset silently on restart. `build_health_report` documents this in
  OPERATIONS.md §4 but cannot correct for it from count/total data alone.
- **Proposed improvement:** windowed aggregation (per-minute buckets or
  external TSDB) as part of the DI-009 metrics-sink work.
- **Dependencies:** metrics sink decision (shared with DI-009). **Risk:**
  recent degradation masked by historical volume; restart-induced amnesia.
- **Acceptance:** rates computed over explicit windows with documented
  retention.
- **Implementation (P1-21, 2026-10-12, process-local only):** 900 s rolling
  windows over monotonic timestamps for all event series (bounded deque,
  4096/series) + windowed RAG/LLM failure-rate indicators reusing lifetime
  state rules (empty window → unknown); lifetime totals/means unchanged;
  16 focused tests; OPERATIONS.md + phase report
  `OBSERVABILITY_WINDOW_AND_LATENCY_P1_21.md`. No endpoint, no sink.
- **Remaining:** sink export decision (DI-009), cross-worker aggregation
  (DI-013) — process-local windows explicitly do not solve those; window
  length is provisional. DI-015 stays open.
- **Export/alert design (P1-22, 2026-10-12, documentation only):**
  `METRICS_EXPORT_AND_ALERT_READINESS_P1_22.md` compares authenticated
  endpoint / pull / push / logs-interim (D works today; A blocked on
  DI-014; C alone enables DI-013 structurally; B moot without a stack),
  with a versioned export contract and alert-readiness gates. No option
  approved or implemented. DI-015 stays open.

## DI-016 — Mean-only latencies hide tail behavior

- **Priority:** P3. **Category:** observability. **Status:** open.
- **Limitation and evidence:** only arithmetic means are accumulated
  (count + total by design, to stay bounded and dependency-free); p95/p99
  outliers — the first symptom of embedding-model or provider trouble —
  are invisible.
- **Proposed improvement:** bounded histogram or reservoir sketch if a
  latency SLO is ever defined; until then, means plus failure counts.
- **Dependencies:** latency objectives worth enforcing. **Risk:** slow-tail
  degradation unnoticed while means look healthy.
- **Acceptance:** tail-latency visibility with storage bounds documented.
- **Implementation (P1-21, 2026-10-12):** windowed count/mean/p50/p95/max
  (ms, linear interpolation over a bounded 1024-sample in-window buffer)
  for `rag.query`/`llm.generate`; empty → nulls with count 0; garbage
  samples ignored; 16 focused tests. No p99 (buffer-exact p95/max chosen
  over a second approximation structure), no latency thresholds set.
- **Remaining:** latency SLOs worth enforcing, sink-side tail aggregation.
  DI-016 stays open.

## DI-017 — Benchmark has no intent/maliciousness dimension

- **Priority:** P2. **Category:** evaluation. **Status:** open.
- **Limitation and evidence:** P1-6 audit found the benchmark format cannot
  distinguish relevance from malice: `no_match` records only whether a
  technique is described, while RB-016 (likely-benign lockout retrieving
  T1110) carries its relevance-without-malice caveat in free prose
  (`ambiguity` field) because no structured field exists. Downstream
  consumers of benchmark results may misread relevance scores as malice
  evidence.
- **Proposed improvement:** optional `intent` annotation
  (malicious|benign|ambiguous|insufficient-context) in a future benchmark
  version, with evaluator support that keeps current P/R/MRR semantics
  unchanged for existing cases. Suggested (not applied) in RB-016's review
  record as a schema-type proposal. P1-7 official-definition check
  strengthens the case: T1110 is defined around guessing-based access
  attempts, which a post-reset lockout does not involve — confirming that
  RB-016's retrieval hit carries zero malice information and the dimension
  gap is real, not hypothetical.
- **Dependencies:** DI-001 analyst review (intent labels need the same
  adjudication). **Risk:** relevance metrics misinterpreted as
  attack-detection metrics.
- **Acceptance:** versioned benchmark with intent annotations adjudicated
  alongside technique labels; evaluator documents how intent is (and is
  not) used in metrics.
- **Protocol completed (P1-19, 2026-10-12, design only, no labels created):**
  `docs/reliability/RAG_INTENT_RELEVANCE_EVALUATION_PROTOCOL.md` defines
  four independent dimensions (relevance incl. parent/sub-technique and
  rival handling reusing benchmark conventions; intent; attribution;
  remediation applicability), reviewer/adjudication/agreement procedures
  (dual review, third-reviewer adjudication, kappa + adjudication rate),
  dev/held-out separation with v1/v2 leakage controls, separate per-dimension
  metrics with fixed denominators and Wilson uncertainty (no acceptance
  thresholds set), reporting/promotion rules, relations to DI-010/DI-006/
  DI-012 (threshold passage establishes neither intent nor attribution),
  and a proposed-but-unimplemented future annotation schema. No benchmark
  payload, review record, baseline, fingerprint, or hash altered; no
  synthetic example presented as real evidence.
- **Still outstanding (DI-017 stays open):** DI-001 adjudication (0 of 42
  decided); owner decisions (reviewer count, minimum held-out size,
  predeclared acceptance criteria); approved annotation schema; held-out
  evaluation with agreement statistics.
