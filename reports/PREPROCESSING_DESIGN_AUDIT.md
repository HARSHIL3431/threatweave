# CICIDS2017 Preprocessing Design — Final Audit Report

**Audit Date**: 2026-08-16
**Auditor**: Senior ML Engineer / Cybersecurity Researcher
**Scope**: Complete preprocessing and Isolation Forest experiment design for CICIDS2017 combined dataset

---

## 1. Executive Summary

This audit rigorously reviews all preprocessing and ML-data design decisions for the CICIDS2017 combined dataset (2,830,743 flows × 77 numeric features). The previous design contained **4 rejected decisions**, **9 modified decisions**, and **1 experiment-required decision**. The most critical finding is that the proposed `log10(x+1)` transformation is **mathematically invalid** for 12 features containing negative values, and `contamination = 0.197` is a **fundamental misapplication** of the Isolation Forest parameter.

**Final Verdict**: 🟡 **APPROVED AFTER MINOR DESIGN CHANGES**

The design changes are well-defined, evidence-based, and implementable without redesigning the pipeline architecture.

---

## 2. Existing Design Reviewed

The following existing artifacts were reviewed:

| Artifact | Path | Status |
|:---|:---|:---|
| COMBINED_INTEGRATION_REPORT.md | reports/ | Verified |
| COMBINED_PREPROCESSING_DESIGN.md | reports/ | Partially valid — 4 decisions rejected |
| CICIDS2017_EDA_FINAL_REPORT.md | reports/ | Verified — all 16 major claims confirmed |
| DATA_LEAKAGE_AUDIT.md | reports/ | Verified |
| ISOLATION_FOREST_READINESS.md | reports/ | Mostly valid — contamination recommendation rejected |
| ISOLATION_FOREST_EXPERIMENT_DESIGN.md | reports/ | Updated with this audit |
| DUPLICATE_STRATEGY_FINAL.md | reports/ | Updated with this audit |
| ZERO_DURATION_INF_STRATEGY.md | reports/ | Updated with this audit |
| FINAL_EDA_AUDIT.md | reports/ | Verified |
| PREPROCESSING_RECOMMENDATIONS.md | reports/ | Partially valid — transformation and split design rejected |
| DATASET_QUALITY_REPORT.md | reports/ | Verified |
| DATASET_INVENTORY.md | reports/ | Verified |
| CROSS_DATASET_ANALYSIS.md | reports/ | Verified |

**Previous audit verdicts**: The FINAL_EDA_AUDIT.md (16/18 verified) and the individual EDA reports are thoroughly grounded in evidence. The issues lie in the **preprocessing design decisions**, not in the EDA findings.

---

## 3. Data Lineage

### Complete Lineage Specification

```
RAW CSV FILES (8 files, 2.83M rows)
    ↓ [SHA-256 verification - VERIFIED]
INTEGRATED RAW DATA (CICIDS2017_COMBINED_RAW.csv, 2,830,743 × 81)
    ↓ [Schema validation, label repair]
VALIDATED DATA
    ↓ [Conflict removal: 697 groups, 6,666 rows]
CONFLICT-FREE DATA
    ↓ [Deduplication: ~309,079 rows removed]
CLEAN DATA (~2,521,664 rows)
    ↓ [Metadata isolation: X, y, metadata separated]
SPLIT-READY DATA
    ↓ [Source-day based splitting]
TRAIN (Monday, ~502K) | VAL (Tuesday, ~422K) | TEST (Wed-Fri, 6 sets)
    ↓ [Zero-duration handling with flag + 1μs imputation]
RATE-STABLE SPLITS
    ↓ [NaN resolution via zero-duration recomputation]
NaN-FREE SPLITS
    ↓ [Constant feature removal: -8 features]
REDUCED SPLITS (70 features)
    ↓ [Redundant feature removal: -10 features]
PRUNED SPLITS (60 features + Is_Zero_Duration)
    ↓ [Feature transformation: log1p / signed-log]
TRANSFORMED SPLITS
    ↓ [Optional RobustScaler: fit on train only]
SCALED SPLITS (61 features)
    ↓ [Isolation Forest: train on Monday BENIGN]
TRAINED MODEL
    ↓ [Evaluation on 6 test sets]
FINAL METRICS
```

### Lineage Violations in Previous Design

| Violation | Severity | Description |
|:---|:---|:---|
| Random train/test split | HIGH | Previous design proposed `train_test_split(random_state=42)` — creates temporal leakage |
| Global contamination | HIGH | contamination=0.197 assumes attacks in training data — invalid for benign-only training |
| Invalid log transform | HIGH | log1p(x) is undefined for 12 features with x < -1 |

---

## 4. Duplicate Strategy

### Evidence
- **309,079** exact duplicate rows (10.92% of 2,830,743)
- **111,795** inter-dataset duplicates (across different days)
- **196,278** intra-dataset duplicates (within same day)
- **697** conflicting feature vectors (same features, different labels)
- **6,666** total rows involved in label conflicts

### Conflict Breakdown
| Label Pair | Conflicting Vectors |
|:---|---:|
| BENIGN vs PortScan | 564 |
| BENIGN vs DoS Hulk | 129 |
| BENIGN vs DDoS | 3 |
| BENIGN vs DoS slowloris | 1 |

### Strategy
**Strategy C (Modified)**: Remove all rows in conflicting groups → Deduplicate remaining.

**Pipeline position**: Stage 4 (conflict removal) and Stage 5 (deduplication), BEFORE train/test split.

**Leakage prevention**: All duplicates are removed before splitting, so no identical feature vectors can appear in both train and test.

**Data loss**: ~315,000 rows total (11.1%) — acceptable given that these are artificial clones and label-corrupted rows.

---

## 5. Zero-Duration / Inf Strategy

### Evidence
- **2,867** zero-duration flows (Flow Duration == 0)
- **2,867** Inf in Flow Packets/s (100%)
- **1,509** Inf in Flow Bytes/s (52.6%)
- **1,358** NaN in Flow Bytes/s (47.4%) — these are 0/0 indeterminate forms
- **ALL** 1,358 NaN rows overlap with zero-duration
- **62%** of zero-duration flows are BENIGN

### Strategy
**Strategy B (Approved with Modification)**:
1. Add `Is_Zero_Duration` binary flag (BEFORE modifying Duration)
2. Set `Flow Duration = max(Flow Duration, 1.0)`
3. Recompute `Flow Packets/s` and `Flow Bytes/s` deterministically
4. NaN in Flow Bytes/s is automatically resolved (0/0 → recomputed as 0.0)

**Rejected alternatives**:
- Dropping zero-duration rows: REJECTED (62% benign)
- Dropping rate features: REJECTED (critical for volumetric detection)
- 1 μs without flag: REJECTED (loses semantic information)

---

## 6. NaN Strategy

### Evidence
- **1,358** NaN values in `Flow Bytes/s` ONLY
- **100%** overlap with zero-duration flows
- **Label distribution**: DoS Hulk (949), BENIGN (409)
- **Root cause**: Total Bytes = 0 AND Flow Duration = 0 → 0/0 indeterminate form

### Strategy
NaN values are resolved by the zero-duration handling (Stage 8). When Flow Duration is imputed to 1 μs and Total Bytes = 0, Flow Bytes/s = 0 / (1 × 10⁻⁶) = 0.0.

**No separate imputation step is needed.** Median imputation is retained as a fallback for any residual NaN, fitted on training data only.

---

## 7. Constant Features

### Evidence
8 features verified constant zero across all 2,830,743 rows:

| Feature | Unique Value | Variance |
|:---|:---|:---|
| Bwd PSH Flags | 0 | 0.0 |
| Bwd URG Flags | 0 | 0.0 |
| Fwd Avg Bytes/Bulk | 0 | 0.0 |
| Fwd Avg Packets/Bulk | 0 | 0.0 |
| Fwd Avg Bulk Rate | 0 | 0.0 |
| Bwd Avg Bytes/Bulk | 0 | 0.0 |
| Bwd Avg Packets/Bulk | 0 | 0.0 |
| Bwd Avg Bulk Rate | 0 | 0.0 |

### Action
REMOVE unconditionally. Zero variance provides zero isolation capability.

### Semi-Constant Features
| Feature | Non-Zero Count | Verdict |
|:---|---:|:---|
| Fwd URG Flags | 315 | Retain (experimental removal) |
| CWE Flag Count | 315 | Remove (r=1.0 with Fwd URG Flags) |
| RST Flag Count | ~670 | Retain (experimental removal) |
| ECE Flag Count | ~670 | Remove (r=1.0 with RST Flag Count) |

---

## 8. Redundant Features

### Evidence
23 pairs with |r| ≥ 0.999, organized into 9 canonical groups:

| Group | Retained | Removed |
|:---|:---|:---|
| 1 | Total Fwd Packets | Subflow Fwd Packets, Total Length of Bwd Packets, Subflow Bwd Bytes |
| 2 | Total Backward Packets | Subflow Bwd Packets |
| 3 | Total Length of Fwd Packets | Subflow Fwd Bytes |
| 4 | Fwd Packet Length Mean | Avg Fwd Segment Size |
| 5 | Bwd Packet Length Mean | Avg Bwd Segment Size |
| 6 | Fwd PSH Flags | SYN Flag Count |
| 7 | Fwd URG Flags | CWE Flag Count |
| 8 | Fwd Header Length | Bwd Header Length |
| 9 | RST Flag Count | ECE Flag Count |

### Canonical Selection Rationale
Retained features are chosen by interpretability: direct metric names (Total Fwd Packets) preferred over derived names (Subflow Fwd Packets); standard TCP flag names (PSH, RST) preferred over derived counts (SYN Flag Count).

---

## 9. Transformation Strategy

### CRITICAL FINDING: Previous Design Rejected

The previous design proposed `log10(x+1)` for all heavy-tailed features. This is **mathematically invalid** for 12 features containing negative values.

### Evidence

| Feature | Minimum Value | Negative Count | log1p Valid? |
|:---|---:|---:|:---|
| Fwd Header Length | -32,212,234,632 | 35 | NO |
| Bwd Header Length | -1,073,741,320 | 22 | NO |
| min_seg_size_forward | -536,870,661 | 35 | NO |
| Flow Bytes/s | -261,000,000 | variable | NO |
| Flow Packets/s | -2,000,000 | variable | NO |
| Flow Duration | -13 | variable | NO |
| Flow IAT Mean | -13 | variable | NO |
| Flow IAT Max | -13 | variable | NO |
| Flow IAT Min | -14 | variable | NO |
| Fwd IAT Min | -12 | variable | NO |
| Init_Win_bytes_forward | -1 | variable | NO |
| Init_Win_bytes_backward | -1 | variable | NO |

### Corrected Strategy

**For non-negative heavy-tailed features**: Apply `np.log1p(x)` — standard and valid.

**For features with negative values**: Apply `sign(x) * log1p(|x|)` — preserves sign while compressing tails.

This is a **critical correction** that prevents NaN propagation during transformation.

### Features Not Transformed
TCP flag counts (binary 0/1), Down/Up Ratio, and other bounded features do not need log transformation.

---

## 10. Scaling Strategy

### Evidence
Isolation Forest performs recursive random axis-aligned splits between x_min and x_max. It does NOT use distances. Therefore:
- Scaling does not affect Isolation Forest splitting behavior
- Extreme values affect split-point distribution but do not prevent splitting
- Log transformation already addresses the most extreme heavy tails

### Decision
**Scaling is OPTIONAL for Isolation Forest.** Include RobustScaler for:
1. Pipeline consistency with future supervised models
2. Ensuring features are on comparable scales for interpretability
3. Preventing any potential numerical issues in edge cases

If included, RobustScaler MUST be fitted on training data only.

---

## 11. Metadata and Label Isolation

### Metadata Columns (NEVER model features)
| Column | Purpose |
|:---|:---|
| Source_File | Traceability |
| Source_Day | Splitting, analysis, evaluation |
| Source_Row_Index | Traceability |

### Target Columns (NEVER model features)
| Column | Purpose |
|:---|:---|
| Label | Evaluation, supervised training where applicable |

### Model Feature Columns (61 features)
All 77 original numeric features minus 18 removed (8 constant + 10 redundant) plus 1 added (Is_Zero_Duration) = 60 base features. With Destination Port experimental: 61 total.

**Critical constraint**: After Stage 6 (metadata isolation), verify that no metadata or label column appears in the feature matrix:
```python
assert not any(col in X_train.columns for col in ['Source_File', 'Source_Day', 'Source_Row_Index', 'Label'])
```

---

## 12. Port Leakage Risk

### Evidence
| Attack Type | Port | Association |
|:---|---:|:---|
| FTP-Patator | 21 | 100.0% |
| SSH-Patator | 22 | 100.0% |
| DoS (all types) | 80 | 100.0% |
| DDoS | 80 | 100.0% |
| Web Attacks | 80 | 100.0% |
| Heartbleed | 444 | 100.0% |
| Infiltration | 444 | 100.0% |
| Bot | 8080 | 64.1% |
| PortScan | Various | Distributed |

### Risk Assessment
**HIGH** for memorization. If Destination Port is included, the model can achieve near-perfect classification by learning a port lookup table rather than behavioral anomalies.

### Decision
**EXPERIMENT REQUIRED**: Run Isolation Forest with and without Destination Port. Primary model: WITHOUT port. Ablation: WITH port.

---

## 13. Source-Day Leakage Risk

### Evidence

| Source Day | P(Attack) | Attack Types |
|:---|---:|:---|
| Monday | 0.00% | None |
| Tuesday | 3.10% | FTP-Patator, SSH-Patator |
| Wednesday | 36.48% | DoS Hulk, GoldenEye, slowloris, Slowhttptest, Heartbleed |
| Thursday-Morning | 1.28% | Web Attacks (3 types) |
| Thursday-Afternoon | 0.01% | Infiltration (36 flows) |
| Friday-Morning | 1.03% | Bot |
| Friday-PortScan | 55.48% | PortScan |
| Friday-DDoS | 56.71% | DDoS |

### Leakage Mechanism
If Source_Day were a model feature, the model would learn: "Friday-PortScan = attack", "Monday = benign." This is not anomaly detection — it is day-based classification.

### Decision
**Source_Day is NEVER a model feature.** It is used ONLY for splitting and evaluation stratification.

---

## 14. Training Population

### Evidence
- Monday: 529,918 flows, 100% benign, 0 attacks
- All-day benign: 2,273,097 flows across 5 days
- Benign drift exists (HTTPS drops from 26.6% to 13.8% during DDoS)

### Decision
**Primary**: Monday BENIGN only (~502,983 after dedup). Clean baseline, guaranteed zero attack contamination, natural temporal separation.

**Ablation**: All-day BENIGN (~200K stratified sample) to test robustness to benign drift.

---

## 15. Contamination Strategy

### Evidence
- Global attack ratio: 19.70% (557,646 attacks / 2,830,743 total)
- Training on benign only → true contamination = 0.0
- contamination parameter in Isolation Forest defines expected anomaly proportion in TRAINING data

### Decision
**contamination = 0.197 is REJECTED.** It would force the model to classify 19.7% of pure benign training data as anomalies.

**Experimental grid**: contamination ∈ {0.001, 0.005, 0.01, 0.02, 0.05, 0.10}

**Tuning**: Optimize on Tuesday validation set using PR-AUC.

---

## 16. Train / Validation / Test Design

### Architecture
| Split | Source Day | Composition | Purpose |
|:---|:---|:---|:---|
| Training | Monday | 100% Benign | Fit Isolation Forest |
| Validation | Tuesday | 96.9% Benign, 3.1% Attack | Tune contamination, threshold |
| Test 1 | Wednesday | 63.5% Benign, 36.5% Attack | DoS detection |
| Test 2 | Thursday-Morning | 98.7% Benign, 1.3% Attack | Web Attack detection |
| Test 3 | Thursday-Afternoon | 99.98% Benign, 0.01% Attack | Infiltration detection |
| Test 4 | Friday-Morning | 98.9% Benign, 1.1% Attack | Bot detection |
| Test 5 | Friday-PortScan | 44.5% Benign, 55.5% Attack | PortScan detection |
| Test 6 | Friday-DDoS | 43.3% Benign, 56.7% Attack | DDoS detection |

### Leakage Prevention
- No random splitting (temporal boundaries respected)
- No duplicate feature vectors across splits (dedup before split)
- All preprocessing fitted on Monday training only
- Validation used only for development decisions
- Final test sets evaluated exactly once

---

## 17. Evaluation Design

### Primary Metrics
| Metric | Target |
|:---|:---|
| PR-AUC | Maximize |
| F1 Score | Maximize at chosen threshold |
| False Positive Rate | < 5% (target < 1%) |
| Detection Rate @ 1% FPR | Maximize |
| FPR @ 90% Recall | Minimize |

### Cybersecurity-Specific Metrics
| Metric | Importance |
|:---|:---|
| Attack-wise recall | Detects which attacks are missed |
| Attack-wise precision | Reveals false alarm patterns per attack type |
| Confusion matrix | Full error characterization |

### Metrics to Avoid
- Accuracy (misleading with 80/20 imbalance)
- ROC-AUC as sole metric (inflated by large TN)

---

## 18. Attack-Wise Evaluation

All 14 attack classes must be evaluated independently:

| Class | Count | Difficulty | Expected |
|:---|---:|:---|:---|
| DoS Hulk | 231,073 | Easy | High recall |
| PortScan | 158,930 | Easy | High recall |
| DDoS | 128,027 | Easy | High recall |
| DoS GoldenEye | 10,293 | Moderate | Moderate recall |
| FTP-Patator | 7,938 | Moderate | Moderate recall |
| SSH-Patator | 5,897 | Moderate | Moderate recall |
| DoS slowloris | 5,796 | Hard | Low-moderate recall |
| DoS Slowhttptest | 5,499 | Hard | Low-moderate recall |
| Bot | 1,966 | Hard | Low recall |
| Web Attack - Brute Force | 1,507 | Hard | Low recall |
| Web Attack - XSS | 652 | Hard | Low recall |
| Infiltration | 36 | Very Hard | Very low recall |
| Web Attack - Sql Injection | 21 | Very Hard | Very low recall |
| Heartbleed | 11 | Very Hard | Very low recall |

---

## 19. Ablation Experiments

| ID | Experiment | Variation A | Variation B | Primary Metric |
|:---|:---|:---|:---|:---|
| E1 | Destination Port | With Port | Without Port | FPR, Attack-wise Recall |
| E2 | Training Population | Monday BENIGN | All-day BENIGN | PR-AUC |
| E3 | Contamination | 0.001 | 0.01, 0.05 | PR-AUC |
| E4 | Duplicate Strategy | With dedup | Without dedup | Overfitting gap |
| E5 | Zero-Duration | Flag + impute | Exclude rows | DoS Hulk recall |
| E6 | Transformations | With log/scale | Raw features | PR-AUC |
| E7 | Scaling | RobustScaler | No scaling | PR-AUC |
| E8 | max_samples | 256 | 512, 1024 | PR-AUC, training time |

---

## 20. Computational Feasibility

| Metric | Value |
|:---|:---|
| Raw dataset size | 2,830,743 rows × 81 columns |
| DataFrame RAM | 2.35 GB |
| After dedup | ~2,521,664 rows |
| Monday training set | ~502,983 rows × 61 features |
| Training RAM | ~250 MB |
| Isolation Forest training | < 30 seconds (100 trees, max_samples=256) |
| Full pipeline runtime | < 5 minutes |
| Peak RAM | ~4 GB |

No computational barriers. No sampling or chunking required.

---

## 21. Final Preprocessing Pipeline

See `reports/FINAL_PREPROCESSING_DESIGN.md` for the complete 15-stage pipeline specification with exact code, inputs, outputs, parameters, and leakage risk for each stage.

---

## 22. Decision Matrix

See `reports/PREPROCESSING_DECISION_MATRIX.md` for the complete 20-decision evaluation table with verdicts.

---

## 23. Risks and Limitations

### Known Risks

1. **Negative values in features**: 12 features contain CICFlowMeter artifacts (negative header lengths, negative durations). These are likely capture/processing errors. The signed-log transformation handles them mathematically but the resulting values are not physically meaningful.

2. **Benign drift during attacks**: Monday-only training does not expose the model to attack-day benign drift. The all-day benign ablation (E2) will quantify this risk.

3. **Micro-minority classes**: Heartbleed (11), SQL Injection (21), Infiltration (36) cannot be statistically evaluated with confidence. Detection of these classes is a bonus, not a primary metric.

4. **Synthetic testbed**: CICIDS2017 was generated in a controlled lab. Port/behavior patterns may not generalize to production networks. The Destination Port ablation (E1) quantifies testbed-specific memorization.

5. **Single-day training**: Monday may not represent all benign traffic patterns. The all-day benign ablation addresses this.

6. **Contamination sensitivity**: Isolation Forest performance is sensitive to contamination. The experimental grid (E3) will identify the optimal value.

### Limitations

1. No deep packet inspection features available — limited to CICFlowMeter statistical features.
2. No temporal sequence modeling — each flow is treated independently.
3. No protocol-level validation — CICFlowMeter extraction errors (negative values) are treated as-is.

---

## 24. Final Recommendation

### Critical Corrections Required

1. **Log transformation**: Replace `log10(x+1)` with `sign(x) * log1p(|x|)` for 12 features with negative values. Standard `log1p` for remaining non-negative features.

2. **Contamination**: Reject 0.197. Use experimental grid {0.001, 0.005, 0.01, 0.02, 0.05, 0.10}.

3. **Train/test split**: Reject random splitting. Use source-day based splitting.

4. **Duplicate handling**: Add label-conflict removal step before deduplication.

5. **Zero-duration**: Add `Is_Zero_Duration` flag before imputation.

6. **NaN handling**: Resolve via zero-duration recomputation, not separate median imputation.

### All Other Decisions

Approved or approved with minor modifications as documented in the Decision Matrix.

### Final Verdict

# 🟡 APPROVED AFTER MINOR DESIGN CHANGES

**Rationale**: The pipeline architecture (stages, ordering, splitting strategy) is sound. The required changes are:
- Mathematical correction to transformation (critical but localized)
- Parameter correction to contamination (critical but simple)
- Split strategy correction (critical but well-defined)
- Duplicate strategy enhancement (moderate complexity)
- Flag addition for zero-duration (simple addition)

None of these require restructuring the pipeline. All are implementable as modifications to the existing design.

**Ready for implementation after corrections are applied.**

---

## Appendix A: Answers to 30 Critical Questions

1. **Should all duplicates be removed?** Yes — after label-conflict removal (Strategy C).
2. **If not, how will duplicate leakage be prevented?** N/A — all duplicates removed.
3. **What happens if identical features occur with different labels?** Remove all rows in those groups (6,666 rows, 697 groups).
4. **Is 1 μs actually justified for zero-duration flows?** Yes — it is the physical timing floor of CICFlowMeter.
5. **Should Zero_Duration_Flag be added?** Yes — provides explicit semantic signal.
6. **Should Flow Bytes/s and Flow Packets/s be retained?** Yes — critical for volumetric attack detection.
7. **Is median imputation appropriate?** Only as fallback. NaN is resolved by zero-duration handling.
8. **Which constant features should be removed?** All 8 verified constant-zero features.
9. **Which redundant features should be removed?** 10 features as documented in redundancy groups.
10. **Which transformations are actually justified?** log1p for non-negative features; sign(x)*log1p(|x|) for features with negatives.
11. **Does Isolation Forest benefit from scaling?** Not for splitting, but included for pipeline consistency.
12. **Should Destination Port be retained?** Experimental — primary model without, ablation with.
13. **How will port memorization be tested?** Ablation E1: with vs without Destination Port.
14. **Should Source_Day be excluded?** Yes — never a model feature.
15. **Should Source_Dataset be excluded?** Yes — never a model feature.
16. **What exact data should Isolation Forest train on?** Monday BENIGN traffic (~502K unique rows).
17. **Why?** Clean baseline with zero attacks; natural temporal separation from test days.
18. **Is Monday BENIGN sufficient?** Primary design yes; all-day benign ablation available.
19. **Should benign traffic from other days be included?** Evaluated in ablation E2.
20. **How will benign drift be handled?** Quantified via ablation E2; robust scaling helps.
21. **Why is contamination NOT simply 0.197?** Training on benign only → true contamination = 0.0.
22. **How should contamination be selected?** Experimental grid, tuned on Tuesday validation.
23. **How will thresholds be selected?** PR-AUC optimization on validation; FPR-fixed detection rates.
24. **How will train/test leakage be prevented?** Source-day splitting + dedup before split.
25. **How will duplicate groups be handled?** Conflict removal → dedup → clean unique vectors.
26. **How will attack-wise performance be measured?** Per-class recall, precision, F1 for all 14 attacks.
27. **What should the final test set represent?** Each test set = one recording day with its specific attacks.
28. **Which decisions require ablation experiments?** 8 experiments defined (E1-E8).
29. **What is the exact final feature matrix?** 60 base features + Is_Zero_Duration = 61 features (60 + optional Port).
30. **Can the entire pipeline be reproduced?** Yes — all parameters are deterministic or fitted on training data with fixed random seeds.
