# DECISIONS.md

Records all significant technical decisions for the project. Updated as decisions are made.

---

## D001: Primary Dataset
- **Date**: 2026-08-16
- **Decision**: CICIDS2017 is the primary dataset. NSL-KDD is secondary.
- **Evidence**: PRD.md specifies both. CICIDS2017 has richer attack diversity and temporal structure.
- **Status**: IMPLEMENTED

## D002: Combined Dataset Creation
- **Date**: 2026-08-16
- **Decision**: Integrate all 8 CICIDS2017 CSVs into a single combined dataset with provenance tracking.
- **Evidence**: 2,830,743 rows × 81 columns. Schema harmonized, labels sanitized.
- **Status**: IMPLEMENTED (CICIDS2017_COMBINED_RAW.csv)

## D003: Label Conflict Resolution (Strategy C)
- **Date**: 2026-08-16
- **Decision**: Remove all rows with conflicting labels for identical feature vectors, THEN deduplicate.
- **Evidence**: 697 conflicting feature vectors (6,666 rows). Same features labeled as both BENIGN and attack.
- **Status**: IMPLEMENTED in preprocess.py Stage 4

## D004: Zero-Duration Handling (Flag + 1us)
- **Date**: 2026-08-16
- **Decision**: Add Is_Zero_Duration flag, clip Duration to 1us, recompute rates. Do NOT drop rows.
- **Evidence**: 2,867 zero-duration flows. 62% benign. All Inf/NaN caused by Duration=0.
- **Status**: IMPLEMENTED in preprocess.py Stage 8

## D005: Log Transformation Correction
- **Date**: 2026-08-16
- **Decision**: Use log1p for non-negative features, sign(x)*log1p(|x|) for features with negatives.
- **Evidence**: 12 features have negative values. Standard log1p is undefined for x < -1.
- **Status**: IMPLEMENTED in preprocess.py Stage 12

## D006: Source-Day Splitting
- **Date**: 2026-08-16
- **Decision**: Split by source day. Monday=train, Tuesday=val, Wed-Fri=test. NO random splitting.
- **Evidence**: Temporal burst correlation; attack types concentrated by day; duplicates span days.
- **Status**: IMPLEMENTED in preprocess.py Stage 7

## D007: contamination != 0.197
- **Date**: 2026-08-16
- **Decision**: contamination is an experimental parameter, tuned on validation. NOT the global attack ratio.
- **Evidence**: Training on benign only means true contamination = 0.0. 0.197 forces benign to be flagged.
- **Status**: IMPLEMENTED in train.py (tuning grid: 0.001-0.10)

## D008: Destination Port Ablation
- **Date**: 2026-08-16
- **Decision**: Run experiments with and without Destination Port.
- **Evidence**: 12/14 attack types are 100% port-correlated. Port memorization risk is high.
- **Status**: IMPLEMENTED in run_pipeline.py (baseline=no_port, with_port experiment)

## D009: ML Code Location
- **Date**: 2026-08-16
- **Decision**: ML pipeline code lives in demo/scripts/. Project docs in sem 5/Project/.
- **Rationale**: All EDA and analysis work is already in demo/. Keeps code near data.
- **Status**: IMPLEMENTED

## D010: Scaling Optional for Isolation Forest
- **Date**: 2026-08-16
- **Decision**: RobustScaler is optional and disabled by default for Isolation Forest.
- **Evidence**: IF is tree-based; scaling does not affect splitting. Included for supervised model consistency.
- **Status**: IMPLEMENTED in preprocess.py (apply_scaling=False default)

## D011: Contamination Tuning Fitted on TRAIN, Selected on VAL
- **Date**: 2026-08-22
- **Decision**: Corrected tune_contamination(): candidate models are fitted on Monday
  training data for every grid value; Tuesday validation is used exclusively for
  metric-based selection. The previous implementation fitted candidates on X_val,
  which contradicted ISOLATION_FOREST_EXPERIMENT_DESIGN.md §3.3 and invalidated selection.
- **Evidence**: Code inspection pre-run; sklearn semantics (contamination changes only
  offset_, not trees/scores) make PR-AUC identical across contamination values, so the
  documented "max validation PR-AUC" rule could never discriminate. Selection criterion
  changed to max validation F1, tie-break min FPR — exactly the metrics recorded per grid point.
- **Status**: IMPLEMENTED in train.py; recorded in results.json per experiment

## D012: Dual Frozen Operating Points (OP-A / OP-B)
- **Date**: 2026-08-22
- **Decision**: Freeze two operating points per model, both selected without test data:
  OP-A = contamination-implied offset (primary protocol); OP-B = decision threshold
  swept ONLY on Tuesday validation scores (max F1, tie-break min FPR) per design-doc §3.4.
  OP-B was needed because OP-A selections degenerated (E1 grid all-zero F1 → c=0.001;
  E2 → boundary value c=0.10 from 2 noisy TP).
- **Evidence**: Contamination grids in results.json; sweeps in
  data/processed/analysis/E{1,2}_validation_threshold_sweep.csv.
- **Frozen values**: E1 OP-A 0.657668 / OP-B 0.482296; E2 OP-A 0.521919 / OP-B 0.487850.

## D013: ML Baseline Freeze
- **Date**: 2026-08-22
- **Decision**: Freeze preprocessing version, feature lists (59/60), split strategy,
  tuning method and outcomes, both operating points, seed=42, and model params
  (n_estimators=100, max_samples=256). Both artifacts retained: E2 as primary detector
  artifact, E1 as behavioral-only reference/ablation. Any change requires a new experiment ID.
- **Evidence**: FINAL_ML_REPORT.md §17; reproducibility 12/12 PASS
  (scripts/reproducibility_log.txt).
- **Status**: FROZEN

## D014: Artifact-Driven Backend Preprocessing
- **Date**: 2026-09-15
- **Decision**: Backend inference must load the E2 feature order and configured
  log1p/signed-log feature lists from `preprocessing_config.json`, then validate
  them against the model metadata before serving traffic. Zero-duration handling
  remains the frozen `scripts/preprocess.py` convention: flag, 1 microsecond
  duration floor, rate recomputation, then transformations.
- **Evidence**: Backend regression suite passed 34/34, including frozen score and
  prediction consistency plus malformed-config rejection tests.
- **Status**: IMPLEMENTED

## D015: Safe Inference Error Responses
- **Date**: 2026-09-15
- **Decision**: Preserve detailed inference failures in backend logs but expose
  only the generic `INFERENCE_ERROR` message through the API. Artifact and
  configuration failures remain controlled readiness/feature errors.
- **Evidence**: Hardened integration test injects an internal model exception
  and verifies the structured response contains no internal path or secret text.
- **Status**: IMPLEMENTED

## D016: Backend Documentation Set
- **Date**: 2026-09-15
- **Decision**: Keep backend setup, API contract, and architecture documentation
  in `backend/README.md`, `API_CONTRACT.md`, and `ARCHITECTURE.md`. These docs
  describe only implemented behavior and identify MITRE, RAG, LLM, frontend,
  and live-detection work as future scope.
- **Evidence**: Documentation reviewed against the current FastAPI routes,
  Pydantic schemas, service boundaries, frozen E2 artifacts, and 39-test result.
- **Status**: IMPLEMENTED
