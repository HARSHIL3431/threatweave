# CICIDS2017 Isolation Forest Experiment Design — Final Audit

## 1. Executive Summary

This document specifies the complete Isolation Forest experiment design, including training population, contamination strategy, hyperparameters, evaluation metrics, and ablation experiments. It rejects the previous `contamination = 0.197` recommendation and provides an evidence-based alternative.

---

## 2. Training Population

### 2.1 Primary Design: Monday BENIGN Only

**Training data**: All benign traffic from Monday after deduplication (~502,983 unique rows).

**Rationale**:
- Monday contains 100% benign traffic with 0 attacks. This guarantees zero label contamination during training.
- Monday represents a typical enterprise workday with DNS (~40.5%), HTTPS (~26.6%), HTTP (~9.6%) distributions.
- Cross-day evaluation tests genuine generalization: can the model trained on Monday detect attacks on Tuesday-Friday?
- Avoids the computational and methodological complexity of all-day benign training.

**Limitations**:
- Does not expose the model to attack-day benign drift (e.g., reduced HTTPS during DDoS).
- May produce higher false positive rates on days with heavy attack traffic.

### 2.2 Ablation: All-Day BENIGN

**Training data**: Stratified sample of ~200K benign flows from all days.

**Rationale**: Tests whether exposure to benign drift improves robustness.

**Leakage mitigation**: Use day-level splitting — train on Monday + Wednesday benign + Thursday-Morning benign; validate on Tuesday; test on remaining days.

### 2.3 Why NOT All Data with contamination=0.197

Training Isolation Forest on mixed benign+attack data with `contamination=0.197` would:
1. Force the model to classify the 19.7% most extreme training points as anomalies.
2. If training includes attacks, the model learns to separate "normal attacks" from "extreme attacks" — not "normal" from "attack."
3. This fundamentally breaks the anomaly detection paradigm, which requires a clean normal baseline.

---

## 3. Contamination Strategy

### 3.1 Why contamination ≠ 0.197

The global attack ratio (19.7%) is a dataset-level statistic, NOT a training-set property.

- `contamination` in Isolation Forest defines the expected proportion of anomalies in the **training data**.
- If training on purely benign data, the true contamination is 0.0.
- Setting `contamination=0.197` on a pure benign training set forces the model to label 19.7% of benign flows as anomalies, destroying precision.
- The previous design incorrectly conflated dataset composition with training-set contamination.

### 3.2 Experimental Contamination Grid

| contamination | Rationale |
|:---|:---|
| 0.001 | Very conservative: flags only the most extreme outliers |
| 0.005 | Conservative: appropriate for low-FPR IDS requirements |
| 0.01 | Moderate: standard starting point for anomaly detection |
| 0.02 | Moderate-aggressive |
| 0.05 | Aggressive: may capture more attacks but higher FPR |
| 0.10 | Very aggressive: useful as upper bound comparison |

### 3.3 Tuning Protocol

1. Train Isolation Forest on Monday BENIGN with each contamination value.
2. Score Tuesday (validation) data.
3. Compute PR-AUC, F1, FPR at each contamination level.
4. Select contamination that maximizes PR-AUC on validation.
5. Report performance on Wednesday-Friday test sets using the selected contamination.

### 3.4 Threshold Alternative

Instead of relying solely on `contamination`, also evaluate custom thresholding:
1. Use `contamination='auto'` (no forced threshold).
2. Use `model.score_samples()` to get continuous anomaly scores.
3. Sweep threshold on validation set to find optimal operating point.
4. Report detection rate at fixed FPR targets (1%, 5%, 10%).

---

## 4. Isolation Forest Hyperparameters

| Parameter | Primary Value | Range for Experiment |
|:---|:---|:---|
| `n_estimators` | 100 | 100, 200 |
| `max_samples` | 256 | 128, 256, 512, 1024 |
| `max_features` | 1.0 (all) | 0.8, 1.0 |
| `bootstrap` | False | False, True |
| `contamination` | Experimental | 0.001 – 0.10 |
| `random_state` | 42 | Fixed for reproducibility |

### 4.1 max_samples Rationale

The original paper (Liu et al., 2008) shows that `max_samples=256` is effective for most datasets. Subsampling:
- Eliminates swamping (normal points isolated prematurely).
- Eliminates masking (attack clusters hiding each other).
- Reduces computational cost.

For our dataset (~500K training rows), `max_samples=256` means each tree sees 0.05% of the data per build, which is appropriate.

---

## 5. Evaluation Metrics

### 5.1 Primary Metrics

| Metric | Description | Target |
|:---|:---|:---|
| **PR-AUC** | Precision-Recall Area Under Curve | Maximize |
| **F1 Score** | Harmonic mean of precision and recall | Maximize at chosen threshold |
| **False Positive Rate (FPR)** | FP / (FP + TN) | Minimize (target < 5%) |
| **Recall (Detection Rate)** | TP / (TP + FN) | Maximize |

### 5.2 Cybersecurity-Specific Metrics

| Metric | Description | Importance |
|:---|:---|:---|
| **FPR @ 90% Recall** | False positive rate when detecting 90% of attacks | Critical for SOC usability |
| **Detection Rate @ 1% FPR** | Recall when false positive rate is capped at 1% | Critical for production IDS |
| **Attack-wise Recall** | Per-class detection rate for each of 14 attack types | Reveals detection gaps |
| **Attack-wise Precision** | Per-class precision for each attack type | Reveals false alarm patterns |

### 5.3 Metrics to AVOID

| Metric | Why Avoid |
|:---|:---|
| **Accuracy** | Misleading with 80/20 class imbalance |
| **ROC-AUC alone** | Can be inflated by the massive TN count; PR-AUC is more informative for imbalanced data |

---

## 6. Attack-Wise Evaluation

Do NOT evaluate only BENIGN vs ATTACK. Report per-class performance:

| Attack Class | Count | Expected Detection Difficulty |
|:---|---:|:---|
| DoS Hulk | 231,073 | Easy (volumetric) |
| PortScan | 158,930 | Easy (distinctive scan pattern) |
| DDoS | 128,027 | Easy (volumetric) |
| DoS GoldenEye | 10,293 | Moderate |
| FTP-Patator | 7,938 | Moderate (brute-force pattern) |
| SSH-Patator | 5,897 | Moderate (encrypted brute-force) |
| DoS slowloris | 5,796 | Hard (slow, low-rate) |
| DoS Slowhttptest | 5,499 | Hard (incomplete requests) |
| Bot | 1,966 | Hard (low-and-slow C2) |
| Web Attack - Brute Force | 1,507 | Hard (application layer) |
| Web Attack - XSS | 652 | Hard (small payload) |
| Infiltration | 36 | Very Hard (mimics normal) |
| Web Attack - Sql Injection | 21 | Very Hard (small payload) |
| Heartbleed | 11 | Very Hard (rare, unique) |

---

## 7. Ablation Experiment Matrix

| Experiment | Variation A | Variation B | Metric |
|:---|:---|:---|:---|
| **E1: Destination Port** | With Port | Without Port | FPR, Recall, Attack-wise |
| **E2: Training Population** | Monday BENIGN | All-day BENIGN | PR-AUC, FPR |
| **E3: Contamination** | 0.001 | 0.01, 0.05 | PR-AUC, F1 |
| **E4: Duplicate Strategy** | With dedup | Without dedup (grouped split) | Overfitting metrics |
| **E5: Zero-Duration** | 1 μs flag + impute | Exclude rows | Recall on DoS Hulk |
| **E6: Transformations** | With log+scale | Raw features | PR-AUC |
| **E7: Scaling** | RobustScaler | No scaling | PR-AUC |
| **E8: max_samples** | 256 | 512, 1024 | PR-AUC, training time |

---

## 8. Computational Feasibility

| Metric | Value |
|:---|:---|
| Monday training rows (after dedup) | ~502,983 |
| Features | 60 (or 61 with Port) |
| Isolation Forest (100 trees, max_samples=256) | < 30 seconds |
| Isolation Forest (200 trees, max_samples=1024) | < 2 minutes |
| Full dataset loading | ~15-30 seconds |
| Deduplication | ~5-10 seconds |
| Preprocessing (impute + transform + scale) | ~10-20 seconds |
| **Total pipeline runtime** | < 5 minutes |

RAM requirements: ~3-4 GB peak (DataFrame + preprocessing copies).

---

## 9. Reproducibility Requirements

1. Fix `random_state=42` for Isolation Forest.
2. Fix `random_state=42` for any train/test splitting.
3. Save preprocessing parameters (imputer medians, scaler centers/scales) as JSON.
4. Save model hyperparameters as JSON.
5. Save trained model as pickle/joblib.
6. Log all metrics to a structured results file.
