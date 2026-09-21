# CICIDS2017 Combined Dataset — Status Tracker

**Last Updated**: 2026-08-22
**Current Phase**: PHASE 3 ML DETECTION LAYER — COMPLETE (baseline frozen)

---

## Phase Progress

| Phase | Status | Date | Notes |
|:---|:---|:---|:---|
| 1. Individual EDA (8 datasets) | ✅ COMPLETE | 2026-08-16 | All 8 reports verified |
| 2. Final Individual EDA Audit | ✅ COMPLETE | 2026-08-16 | 16/18 claims verified, 2 qualified |
| 3. Controlled Integration | ✅ COMPLETE | 2026-08-16 | 2,830,743 × 81 combined CSV |
| 4. Combined Benchmark EDA | ✅ COMPLETE | 2026-08-16 | 15-class analysis, drift analysis |
| 5. Cross-Dataset Duplicate Analysis | ✅ COMPLETE | 2026-08-16 | 309,079 duplicates, 697 label conflicts |
| 6. Benign Traffic Drift Analysis | ✅ COMPLETE | 2026-08-16 | HTTPS drops 26.6% → 13.8% during DDoS |
| 7. Feature Redundancy Analysis | ✅ COMPLETE | 2026-08-16 | 23 pairs r≥0.999, 9 canonical groups |
| 8. Data Leakage Audit | ✅ COMPLETE | 2026-08-16 | 4 leakage vectors identified |
| 9. Initial Preprocessing Design | ✅ COMPLETE | 2026-08-16 | Previous design had 4 rejected decisions |
| 10. **PREPROCESSING DESIGN AUDIT** | ✅ **COMPLETE** | 2026-08-16 | **4 rejected, 9 modified, 1 experiment** |
| 11. Preprocessing Implementation | ✅ COMPLETE | 2026-08-16 | 15-stage pipeline in preprocess.py |
| 12. Pre-Experiment Validation | ✅ COMPLETE | 2026-08-16 | 23 PASS, 3 WARN, 0 FAIL |
| 13. Isolation Forest Training (E1+E2) | ✅ COMPLETE | 2026-08-22 | Contamination tuned on val; artifacts saved |
| 14. Evaluation & Reporting | ✅ COMPLETE | 2026-08-22 | Per-day + attack-wise + FP analysis; FINAL_ML_REPORT.md |
| 15. Reproducibility Verification | ✅ COMPLETE | 2026-08-22 | 12/12 PASS (scripts/reproducibility_log.txt) |

---

## Current Status

```
COMBINED DATASET
        ↓
EDA + AUDITS COMPLETE ✅
        ↓
PREPROCESSING IMPLEMENTED & VALIDATED ✅
        ↓
E1 + E2 TRAINED, TUNED, EVALUATED ✅
        ↓
REPRODUCIBILITY VERIFIED (12/12) ✅
        ↓
ML BASELINE FROZEN (D013) ✅
        ↓
BACKEND CONTRACT DOCUMENTED ✅
        ↓
NEXT: BACKEND + FRONTEND ← YOU ARE HERE
```

Key result summary (details in reports/FINAL_ML_REPORT.md):
- E1 (59 features, no port): c=0.001, OP-A thr 0.657668 / OP-B thr 0.482296;
  pooled test F1 0.0005 (OP-A) / 0.6123 (OP-B); day PR-AUC 0.03–0.85.
- E2 (60 features, with port): c=0.10, OP-A thr 0.521919 / OP-B thr 0.487850;
  pooled test F1 0.6264 (OP-A) / 0.5858 (OP-B); PortScan PR-AUC 0.507 vs E1 0.032.
- Volumetric DoS/DDoS detectable; Patator/Bot/Web/Infiltration not, at usable precision.

---

## Completed Deliverables

### Reports (14 files in reports/)
| Report | Status | Key Finding |
|:---|:---|:---|
| CICIDS2017_EDA_FINAL_REPORT.md | ✅ Final | 16/18 claims verified |
| FINAL_EDA_AUDIT.md | ✅ Final | Approved for preprocessing |
| COMBINED_INTEGRATION_REPORT.md | ✅ Final | 2.83M rows integrated |
| COMBINED_PREPROCESSING_DESIGN.md | ⚠️ Superseded | 4 decisions rejected by audit |
| DATA_LEAKAGE_AUDIT.md | ✅ Final | 4 leakage vectors |
| ISOLATION_FOREST_READINESS.md | ⚠️ Updated | Contamination corrected |
| DUPLICATE_STRATEGY_FINAL.md | ✅ Updated | Strategy C (conflict + dedup) |
| ZERO_DURATION_INF_STRATEGY.md | ✅ Updated | Flag + 1μs + recompute |
| ISOLATION_FOREST_EXPERIMENT_DESIGN.md | ✅ Updated | Full experiment matrix |
| FEATURE_SELECTION_DECISIONS.md | ✅ New | 61 features (60 + Port exp.) |
| ML_SPLIT_STRATEGY.md | ✅ New | Source-day based splitting |
| PREPROCESSING_DECISION_MATRIX.md | ✅ New | 20 decisions with verdicts |
| **PREPROCESSING_DESIGN_AUDIT.md** | ✅ **New** | **Main 24-section audit** |
| **FINAL_PREPROCESSING_DESIGN.md** | ✅ **New** | **15-stage pipeline spec** |

### Data Files
| File | Status | Size |
|:---|:---|:---|
| CICIDS2017_COMBINED_RAW.csv | ✅ Unmodified | 1.05 GB |
| 8 Original CSVs (dataset/) | ✅ Unmodified | SHA-256 verified |

### Scripts
| Script | Purpose |
|:---|:---|
| audit_analysis.py | Audit data verification |
| audit_analysis2.py | Extended audit analysis |
| combine_phase2_4_integration.py | Integration pipeline |
| combine_phase5_eda.py | Combined EDA |
| preprocess.py | 15-stage leakage-safe preprocessing pipeline |
| train.py | Isolation Forest training + evaluation |
| run_pipeline.py | End-to-end experiment runner (E1, E2) |
| validate_gate.py | Pre-experiment validation (16 checks) |

---

## Blocked Items

None. ML phase is complete and frozen.

---

## Next Phase

**Backend + Frontend**
- Start from `reports/ML_BACKEND_HANDOFF.md` (frozen input/output contract)
- Model artifacts: `data/processed/experiments/{baseline_no_port,with_port}/model.pkl`
- Do not modify preprocessing, split, thresholds, or models (DECISIONS.md D013)
