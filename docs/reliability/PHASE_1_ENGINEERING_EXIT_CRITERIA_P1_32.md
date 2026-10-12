# Phase 1 Engineering Exit Criteria & Evidence Matrix (P1-32)

Documentation and read-only audit. Statuses: **verified in this phase**
(fresh read-only checks below), **prior-report** (earlier executed runs,
not re-run here), **blocked** (missing human/owner/infra input), **open**
(work remaining). Nothing here closes an item or approves production use.

## 0. Freshly verified in this phase (2026-10-12, non-destructive)

- Backend collection: **456 tests collect, 0 collection errors**
  (`python -m pytest tests --collect-only -q`, backend/).
- Frontend specs listed: **16 tests in 1 file** (`npx playwright test --list`).
- CLI syntax: `check_rag_baseline.py`, `eval_guard_harness.py`
  (`readiness|measure`), `eval_rag_benchmark.py` `--help` all parse.
- Fixture hashes identical to every prior phase (v1 `9314852a36a3`, v2
  `7a77a797cffd`, queue `8c10fc81cbbf`, baselines
  `d131aaf60e07`/`1d65e33b84c3`, guard-eval `c88bd2555e2f`); queue
  42 pending / 0 decided.

## 1. Criterion matrix

ID | Exit criterion | Risk addressed | Verification | Expected evidence | Status | Depends | Owner/approval | Failure response
---|---|---|---|---|---|---|---|---|
A1 | E2 `with_port` primary; 60 features; `-score_samples()`; score ≥ frozen threshold; OP-A `0.5219193851693676`, OP-B `0.4878500998020172`; no silent E1 fallback | Silent model/threshold drift | Prior: `test_detector_regression.py` + `test_ml_service.py` (454-pass suite P1-25); fresh: collection lists threshold-boundary + feature-contract tests | Green suite; contract tests present | prior-report | frozen artifacts | engineering lead | block exit; investigate artifact change
A2 | Split caveats, family blindness, CICIDS2017 limits accurately described | Overclaiming generalization | Read `DETECTOR_EVALUATION_REPORT.md`, DI-005 entry | Same-lab caveats, per-family gaps stated | prior-report | disjoint data (absent) | research owner | block production claims, not exit
B1 | Index/metadata positional + dimensional integrity; fail-closed on corruption | Misattributed techniques | Prior: `test_vectorstore_integrity.py`, `test_rag_service.py` | Green suite | prior-report | — | engineering lead | block exit
B2 | Evaluator + baseline gate behave (compat checks, regression fails, references untouched) | Silent retrieval regression | Prior: 23 gate tests + `test_rag_evaluation.py` + `test_label_review.py`; fresh: gate `--help` parses | Green suite; gate script present | prior-report | — | engineering lead | block exit
B3 | Adjudication state honest: 42 pending/0 decided; labels synthetic; provenance unknown where unproven | Tuning/claiming on unvalidated labels | Fresh: queue counts + hashes above; provenance absent in metadata | 42/0, hashes match, `built_at: null` | verified in this phase | reviewers (DI-001) | owner sign-off | block any label-dependent promotion
B4 | No unapproved threshold, margin, filter, or rebuild | Stealth behavior change | Fresh: grep-equivalent review in P1-30/31 (no floor in retrieval path; builder unexecuted) | No threshold code in `rag_service.py`/`vector_store.py` | prior-report | owner criteria | owner | block exit on any finding
C1 | Validator + synthetic harness green; Track A (35/0/19/1) separate from Track B (0 samples) | Overstating guard reliability | Prior: 454-pass suite incl. guard tests; report `guard_eval_report_v1.json` | Green suite; versioned report | prior-report | — | engineering lead | block exit
C2 | Track B blocked status honest; no fabricated samples | Fake real-model evidence | Fresh: manifest 4 inputs/0 annotated; readiness BLOCKED (P1-25) | Manifest + readiness record | verified in this phase | authorization + credential + analysts | owner | block production-safety claims
C3 | Known lexical gaps + rubric limits documented, not claimed fixed | Semantic overtrust | Read gap audit + hardening + evaluation protocol docs | G-01–G-08 + G-07 boundary stated | prior-report | Track B | owner | block safety claims, not exit
D1 | In-process windows/tails behave; no service-wide claim | Local numbers misread as fleet | Prior: 15 window tests + ops-health suite; fresh: constants verified in code | Green suite; `WINDOW_SECONDS = 900` confirmed | prior-report | — | engineering lead | block exit
D2 | No unauthenticated metrics endpoint; DI-009/013/014/015/016 open | Public ops surface; premature closure | Fresh: repo-wide search zero auth/metrics surface (P1-31 re-confirmed) | No route; items open | verified in this phase | auth review, sink, SLOs | security + infra owners | block any exposure; block closure
E1 | Scores/severity/confidence/candidates communicated honestly; samples labeled; PDFs labeled | User overtrust | Prior: 16/16 browser checks + report string tests + `next build` green | P1-24/27 reports | prior-report | operator study (DI-008), calibration (DI-007) | product owner | fix copy; block accuracy claims
E2 | No calibrated-probability/generalization/production-accuracy claims | False assurance | Fresh: `F1-validated`/`Risk-based`/`probabilistic` absent (P1-24 edits present) | Wording audit | verified in this phase | calibration data | owner | block claims, not exit
F1 | Tests/scripts locatable + runnable from documented commands | Unverifiable exit | Fresh: collection + `--list` + `--help` outputs above | This section | verified in this phase | — | engineering lead | repair docs/env, re-run
F2 | Hashes pinned; working tree preserved; no unapproved modifications | Silent artifact drift | Fresh: hashes + status above | Matching hashes; pre-existing changes intact | verified in this phase | — | engineering lead | block exit; investigate
F3 | Outcomes recorded without fabrication | Audit theater | This document distinguishes fresh vs prior evidence throughout | Honest attribution | verified in this phase | — | audit owner | re-verify

## 2. Acceptance rules

- Engineering gates (A1, B1, B2, C1, D1, F1–F3): must be green/verified
  for research-prototype exit. Current posture: met via prior-report
  greens + fresh checks above (suites last fully green P1-25/P1-27 runs).
- Production gates (A2-claims, B3-promotions, B4, C2-claims, C3-claims,
  D2-exposure, E1-reception, E2-calibration): each needs its listed owner
  approval + evidence; all currently unmet by design. No numeric targets
  invented — every threshold/SLO/agreement value is an explicit owner
  decision.
- Failure blocks engineering exit only for engineering gates; production
  items block production readiness (and their specific capability), never
  the prototype exit — unless an approved criterion says otherwise.

## 3. Ordered verification sequence (future authorized exit review)

1. `git status --short`, `git log --oneline -1` (tree preserved; 2 min, read-only).
2. Fixture/baseline hash check (script §0; mismatch ⇒ stop).
3. `python -m pytest tests/unit/test_label_review.py tests/unit/test_baseline_gate.py -q` (queue + gate; fast, offline).
4. `python scripts/eval_guard_harness.py --out $TEMP/g.json` (Track A reproduces TP35/FN0/TN19/FP1; writes outside repo).
5. `python scripts/eval_guard_track_b.py readiness` (expect BLOCKED; any READY requires authorization review).
6. Full `python -m pytest tests -q` backend (minutes, offline; P1-25: 454 passed).
7. `npx tsc --noEmit`, `npx eslint <changed files>`, `npm run build` frontend (P1-27 green).
8. `npx playwright test` (needs built frontend + backend on :8001; P1-27: 16/16).
9. Long-running detector re-evaluation, baseline regen, index rebuild: NEVER in exit review without separate authorization.

## 4. Preserved limitations (reconciled with register — no status changes)

DI-003/DI-011 completed; DI-001 blocked (42/0); DI-004 blocked
(release/snapshot/approval/sign-off); DI-006/010 blocked (Track B +
human review); DI-007/008 open (calibration/operator data); DI-009/013/
014/015/016 open (option/auth/aggregation/SLO decisions); DI-012/017
open (labels + criteria); DI-005 open (disjoint data); DI-002 open
(validated labels + policy proof). Detector uncalibrated; labels
synthetic; observability process-local; Track A synthetic-only.
Assessment stands: **engineering-exit-ready research prototype; not
production-ready.**
