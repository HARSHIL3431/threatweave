# CICIDS2017 Train / Validation / Test Split Strategy

## 1. Executive Summary

This document specifies the leakage-safe train/validation/test split strategy for the CICIDS2017 preprocessing and Isolation Forest experiment. The design addresses duplicate groups, source-day concentration, temporal burst correlation, and benign drift.

---

## 2. Split Design Principles

1. **No duplicate feature vectors across splits**: After conflict removal and deduplication, no identical feature vectors should appear in both train and test.
2. **No temporal leakage**: Attack bursts should not bridge train/test boundaries.
3. **Source-Day awareness**: The model must not see test-day data during training.
4. **Stratified class representation in validation**: The validation set must contain representative samples of attack classes for threshold tuning.
5. **Final test set is held ONCE**: No preprocessing, feature selection, or hyperparameter decisions should use the final test set.

---

## 3. Split Architecture

### 3.1 Cross-Day Evaluation Protocol (Primary Design)

This design uses natural temporal separation between recording days:

| Phase | Data Source | Composition | Purpose |
|:---|:---|:---|:---|
| **Training** | Monday (all rows after dedup) | 100% Benign (~500K rows) | Fit Isolation Forest on pure normal traffic |
| **Validation** | Tuesday (Benign + Patator) | ~96.9% Benign, ~3.1% Attack | Tune contamination, threshold selection |
| **Test Set 1** | Wednesday (Benign + DoS + Heartbleed) | ~63.5% Benign, ~36.5% Attack | Evaluate DoS detection |
| **Test Set 2** | Thursday Morning (Benign + Web Attacks) | ~98.7% Benign, ~1.3% Attack | Evaluate Web Attack detection |
| **Test Set 3** | Thursday Afternoon (Benign + Infiltration) | ~99.98% Benign, ~0.01% Attack | Evaluate rare attack detection |
| **Test Set 4** | Friday Morning (Benign + Bot) | ~98.9% Benign, ~1.1% Attack | Evaluate Botnet detection |
| **Test Set 5** | Friday PortScan (Benign + PortScan) | ~44.5% Benign, ~55.5% Attack | Evaluate PortScan detection |
| **Test Set 6** | Friday DDoS (Benign + DDoS) | ~43.3% Benign, ~56.7% Attack | Evaluate DDoS detection |

### 3.2 Rationale

- **Monday as training set**: Monday contains 100% benign traffic with 0 attacks. This provides a clean, uncontaminated baseline for the anomaly detector. The model learns what "normal" looks like without any attack contamination.
- **Tuesday as validation**: Tuesday contains brute-force attacks (FTP/SSH Patator) which represent a different attack category than Wednesday's DoS attacks, providing a fair validation benchmark.
- **Wednesday-Friday as test sets**: These provide progressive evaluation across attack types with increasing diversity.
- **No random splitting**: Random splitting would distribute attack bursts across train/test, creating temporal leakage. Cross-day evaluation uses natural temporal boundaries.

### 3.3 Handling Duplicates Across Days

After applying the Strategy C duplicate resolution (remove conflicts, then deduplicate):

1. All rows in the dataset are unique feature vectors with deterministic labels.
2. Since inter-dataset duplicates are resolved by deduplication, no identical feature vectors span train/test.
3. **Verification**: After dedup, confirm zero overlapping feature vectors between train and each test set.

---

## 4. Data Flow

```
RAW COMBINED (2,830,743 rows)
    ↓
SCHEMA VALIDATION
    ↓
CONFLICT REMOVAL (remove 6,666 rows with label conflicts)
    ↓
DEDUPLICATION (remove ~302,000 duplicate rows)
    ↓
CLEAN DATASET (~2,521,664 rows)
    ↓
┌─────────────────────────────────────────┐
│ SOURCE-DAY SPLITTING                     │
│                                           │
│ TRAIN:    Monday (~529,918 → ~502,983 after dedup)   │
│ VAL:      Tuesday (~445,909 → ~421,844 after dedup)  │
│ TEST 1:   Wednesday                       │
│ TEST 2:   Thursday-Morning                │
│ TEST 3:   Thursday-Afternoon              │
│ TEST 4:   Friday-Morning                  │
│ TEST 5:   Friday-PortScan                 │
│ TEST 6:   Friday-DDoS                     │
└─────────────────────────────────────────┘
    ↓
TRAIN-FITTED PREPROCESSING (fit on Monday only)
    ↓
TRANSFORM ALL SPLITS
    ↓
ISOLATION FOREST (train on Monday, evaluate on Tue-Fri)
```

---

## 5. Alternative Split Design: All-Day Benign Training

For the ablation experiment comparing Monday-only vs. all-day benign training:

| Split | Composition |
|:---|:---|
| **Training** | Stratified sample of BENIGN traffic from all days (~200K rows) |
| **Validation** | Tuesday (benign + attack) |
| **Test** | Same 5 test sets as primary design |

**Critical constraint**: When sampling benign traffic from all days for training, ensure that no temporal subset of test-day benign traffic is included in training. Use day-level splitting: e.g., train on Monday + Wednesday benign + Thursday-Morning benign, validate on Tuesday, test on remaining days.

**Leakage risk**: If random sampling of all-day benign includes benign flows from the same time window as test-day attacks, this creates mild temporal leakage. Mitigate by sampling only from periods远离 attack windows.

---

## 6. Validation Set Design

The validation set (Tuesday) serves multiple purposes:

1. **Contamination tuning**: Evaluate Isolation Forest at contamination ∈ {0.001, 0.005, 0.01, 0.02, 0.05, 0.1}.
2. **Threshold selection**: If using custom thresholding (score_samples), find the threshold that maximizes F1 or PR-AUC on validation.
3. **Preprocessing comparison**: Compare different preprocessing strategies (with/without log transform, with/without scaling).
4. **Ablation decisions**: Evaluate with/without Destination Port.

**Important**: Tuesday is NOT used for final evaluation. All metrics on Tuesday are for development decisions only. The final performance report uses Wednesday-Friday test sets.

---

## 7. Final Test Set Protocol

Each test set (Wednesday through Friday) is evaluated ONCE for final reporting.

**Protocol**:
1. Train Isolation Forest on Monday training data.
2. Fit preprocessing on Monday training data.
3. Transform test data using training-fitted preprocessing.
4. Score test data.
5. Apply threshold (chosen from validation).
6. Compute metrics.
7. **DO NOT retune any parameters based on test results.**

---

## 8. Verification Checklist

Before proceeding to implementation:

- [ ] Confirm zero duplicate feature vectors between Monday training and each test set.
- [ ] Confirm zero label-conflicting rows remain after Strategy C.
- [ ] Confirm all preprocessing parameters are fitted on Monday training only.
- [ ] Confirm validation set (Tuesday) is used only for development decisions.
- [ ] Confirm final test sets are evaluated exactly once.
