# Controlled Engineering Verification (P1-33)

Fresh execution of the P1-32 sequence on `main` @ `e91ca2c`. Verification
only: no production code, artifact, fixture, baseline, queue, threshold,
contract, or copy was changed to make anything pass.

## 1. Preflight and starting snapshot

Branch `main`, HEAD `e91ca2c`, working tree preserved as found. Starting
hashes (sha256-16): model.pkl `559fdb30a1b88a8a`, preprocessing
`92cc44709c3218a8`, index.faiss `3947e066016419af`, metadata
`927c4a00c95c7722`, benchmarks `9314852a36a340fe`/`7a77a797cffdf15f`,
queue `8c10fc81cbbf9a90` (42/42 pending), baselines
`d131aaf60e07abe0`/`1d65e33b84c3f01d`.

## 2. Results by step (commands verbatim, backend/ unless noted)

- **B** `python -m pytest tests/unit/test_detector_regression.py
  tests/unit/test_ml_service.py tests/unit/test_detector_evaluation.py
  tests/unit/test_severity_service.py
  tests/unit/test_confidence_risk_semantics.py -q` → **46 passed**.
  Covers E2 with_port primary, 60 features, `-score_samples()`,
  score ≥ threshold, frozen OP-A/OP-B, no E1 fallback.
- **C** `... test_vectorstore_integrity.py test_rag_service.py
  test_rag_evaluation.py test_baseline_gate.py test_label_review.py
  test_threshold_derivation.py test_mitre_provenance.py
  test_mitre_data.py -q` → **131 passed**.
- **D** `... test_explanation_grounding.py test_remediation_grounding.py
  test_llm_guard_boundaries.py test_llm_service.py
  test_guard_eval_harness.py test_guard_track_b.py -q` → **152 passed**.
  Track A vs Track B kept separate (synthetic report vs BLOCKED
  readiness); no live calls.
- **E** `... test_observability.py test_observability_windows.py
  test_ops_health.py -q` → **42 passed**; snapshot keys verified
  (`events`, `mean_latency_ms`, `window_events`, `latency_ms`, …);
  repo-wide search confirms **no metrics route** under `app/api`.
- **F** `python -m pytest tests -q` → **454 passed, 2 skipped**
  (pre-existing opt-in real-LLM skips), exit 0. No code touched to get
  there.
- **G** `npx tsc --noEmit` clean; `npx eslint` on the five P1-24 files
  clean; `npm run build` green (compile + types + 11 pages);
  `npx playwright test` → **16/16** (light + dark-narrow) against
  documented `uvicorn :8001` + `next start :3000` workflow. Live spot
  checks via backend: anomalous `true/0.5402/medium`, benign
  `false/0.4518/info`, RAG T1595 top — functionality available.
- **H** Report/PDF suites included in F (report_service, report_trust,
  report_api all green); sample-PDF bytes asserted `%PDF-` + approved
  wording in the browser run. Temp outputs only (pytest tmp, Playwright
  downloads); no user reports created.

## 3. Failures, skips, observations

- **Zero failures.** 2 skips = pre-existing opt-in real-LLM tests
  (credential-gated by design; skipped ≠ passed, recorded as such).
- Observation (non-failure): one `ClientDisconnected` traceback in the
  verification backend log on `/api/v1/rag/status` — a probed client
  disconnecting mid-response, handled by the sanitized catch-all;
  classified environmental/inconclusive, no criterion affected (all
  dependent checks passed).
- No stale expectations, missing dependencies, or unavailable services
  encountered; servers started per documented workflow and stopped after
  verification (ports verified down; unrelated processes untouched).

## 4. Final integrity (Step I)

All nine Step-A hashes **identical** at close; queue still 42 pending /
0 decided; `git diff --check` clean; `git status --short` shows only
pre-existing modifications plus untracked phase artifacts (this report
added under `docs/`). No unexpected generated files retained in-repo
(Playwright `test-results/` removed after P1-27 precedent; fresh run
artifacts likewise ephemeral).

## 5. Exit-readiness recommendation

Fresh evidence supports **engineering exit as a research prototype**:
frozen detector/RAG/guards/observability behaviors reproduce green,
hashes pin artifacts, copy verified in a real browser, and every open
item remains honestly open with a named path. **Production readiness is
not established** — DI-001/004/006/010 adjudication and approvals,
owner criteria and SLOs, Track B data, calibration/operator/disjoint
evidence, and export/auth/alert infrastructure all remain outstanding
per the P1-32 matrix. Proceed to P1-34 (owner review) on this evidence;
do not proceed to production deployment.
