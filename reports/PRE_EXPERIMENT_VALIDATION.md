# Pre-Experiment Validation Report

**Date**: 2026-08-16
**Dataset**: CICIDS2017_COMBINED_RAW.csv
**Status**: YELLOW: READY AFTER MINOR FIXES

## Results

| Check | Status | Detail |
|:---|:---|:---|
| S1_SPLIT_COUNTS | [YELLOW] | Some counts differ from expected (may reflect dedup differences) |
| S1_COVERAGE | [GREEN] | 0 unassigned rows |
| S1_TRAIN_PURE | [GREEN] | Training (Monday) is 100% BENIGN |
| S2_LEAKAGE | [GREEN] | No forbidden columns in feature matrix (59 clean features) |
| S3_TRAIN_VAL_COLS | [GREEN] | X_train == X_val columns (59 features) |
| S3_TRAIN_TEST_COLS | [GREEN] | All X_test splits match X_train columns |
| S3_DTYPES | [GREEN] | All features are float64 (after transform) |
| S5_RAW_DUPS | [YELLOW] | 78353 raw rows span splits (handled by dedup) |
| S5_POST_DEDUP | [GREEN] | Stage 4+5 remove all conflicts and duplicates before splitting |
| S6_CONFLICTS_REMOVED | [GREEN] | All 697 conflicting groups removed |
| S7_NAN_INF | [GREEN] | All splits: NaN=0 Inf=0 |
| S8_ZERO_DUR_FLAG | [YELLOW] | Flag count 796 differs from raw 2867 (after dedup) |
| S8_DUR_FLOOR | [GREEN] | Flow Duration post-signed_log min=0.693147 (expected log1p(1.0)=0.693147 = clip floor) |
| S8_NO_INF_RATES | [GREEN] | No Inf in rate features |
| S9_BWD_HEADER | [GREEN] | Bwd Header Length fully removed |
| S9_SIGNED_LOG_CLEAN | [GREEN] | All signed-log features clean |
| S10_FEATURE_COUNT | [GREEN] | E1 (no port): 59 features (expected 59) |
| S10_DOC_MATCH | [GREEN] | Matches expected count for port configuration |
| S11_PORT_ABLATION | [GREEN] | E2 has exactly 1 extra feature (Destination Port) |
| S12_TRAIN_BENIGN_ONLY | [GREEN] | Training is 100% BENIGN |
| S12_NO_LABEL_IN_FIT | [GREEN] | IsolationForest.fit(X.values) — labels not passed |
| S13_NO_0197 | [GREEN] | 0.197 not hardcoded |
| S13_TUNED | [GREEN] | Contamination tuned on validation set (Tuesday) |
| S14_TEST_ISOLATED | [GREEN] | Test data used only in evaluate_split() — evaluation-only |
| S15_MEMORY | [GREEN] | Peak ~3.42 GB (within 8 GB) |
| S16_OUTPUTS | [GREEN] | Experiments write to data/processed/experiments/<name>/ — no overwriting |

**Summary**: 23 PASS, 3 WARN, 0 FAIL

## Command

```bash
cd demo/scripts
python run_pipeline.py --experiment all
```
