# CICIDS2017 Isolation Forest Readiness Assessment

## 1. Executive Summary
This document evaluates the readiness of the CICIDS2017 dataset suite for unsupervised and semi-supervised anomaly detection experiments using **Isolation Forest (`iForest`)**. We systematically assess data dimensionality, scale sensitivity, outlier mechanics, contamination assumptions, and experimental design.

---

## 2. Dimensionality & Feature Pruning Requirements
- **Raw Feature Count**: 78 raw features + 1 duplicate column.
- **Mandatory Pruning Before Isolation Forest**:
  1. **Duplicate Column**: Drop column index 34 (`Fwd Header Length.1`).
  2. **8 Global Constant Columns**: Remove `Bwd PSH Flags`, `Bwd URG Flags`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate` (zero variance provides 0 isolation capability).
  3. **Semi-Constant Columns**: Remove `Fwd URG Flags` and `CWE Flag Count` (near-zero variance, constant in 7 of 8 days).
  4. **Port Number**: Drop `Destination Port` for domain-general behavioral anomaly detection.
- **Effective Active Dimension**: **65 to 68 clean numerical flow metrics**.

---

## 3. Scale, Skewness, and Splitting Dynamics
- **Tree Splitting Mechanics**:
  - Isolation Forest performs recursive random axis-aligned partition cuts between $x_{min}$ and $x_{max}$ for randomly chosen features.
- **Impact of Extreme Skewness**:
  - Features such as `Flow Duration`, `Flow Bytes/s`, `Flow Packets/s`, and `Total Length of Bwd Packets` span 8 orders of magnitude ($0$ to $10^8$).
  - When cutting uniformly between $x_{min}$ and $x_{max}$, a feature with an extreme outlier ($10^8$) will almost certainly pick a random cut-point that isolates the single outlier at depth 1.
  - **Remedy**: Apply logarithmic transformation ($\log_{10}(x + 1)$) or robust quantile scaling to prevent random cut-points from degenerating into trivial single-point isolators.

---

## 4. Infinite & Missing Value Preconditions
- **Requirement**: Isolation Forest implementations (e.g., `scikit-learn.ensemble.IsolationForest`) fail on `NaN` or `+Inf`/`-Inf`.
- **Mandatory Imputation Strategy**:
  - `Flow Bytes/s` and `Flow Packets/s` containing `+Inf` (caused by `Flow Duration == 0`) must be deterministically imputed (e.g., replace with maximum observed finite value or compute with a virtual duration denominator of 1 µs).
  - Missing `NaN` values (64 in Monday, 1,008 in Wednesday) must be imputed with median or 0.

---

## 5. Optimal Training Population & Contamination Strategy
- **Baseline Training Recommendation**:
  - **Train Dataset**: `Monday-WorkingHours.pcap_ISCX.csv` (100% Benign).
  - Training on a 100% benign baseline ensures the anomaly detector learns the uncorrupted distribution of enterprise traffic.
  - Set `contamination='auto'` or calibrate against a small labeled validation slice (e.g., Tuesday Patator).
- **Subsampling Parameters (`max_samples`)**:
  - Set `max_samples=256` to `1024` with `n_estimators=100`–`200`. Subsampling is mathematically proven to eliminate *swamping* (normal points isolated prematurely) and *masking* (attack clusters hiding each other).

---

## 6. Evaluation Protocol (Cross-Day Generalization)
| Phase | Dataset Used | Expected Composition | Evaluation Metric |
| :--- | :--- | :--- | :--- |
| **Train** | Monday (Deduplicated Benign) | 100% Benign (~500k flows) | Calibration / In-distribution score |
| **Test 1: Brute Force** | Tuesday | 96.9% Benign, 3.1% Patator | ROC-AUC, PR-AUC, Detection Rate @ 1% FPR |
| **Test 2: DoS / Heartbleed** | Wednesday | 63.5% Benign, 36.5% DoS | ROC-AUC, PR-AUC, Detection Rate @ 1% FPR |
| **Test 3: Web Attacks** | Thursday Morning | 98.7% Benign, 1.3% Web Attacks | PR-AUC (Imbalanced Precision-Recall) |
| **Test 4: Infiltration** | Thursday Afternoon | 99.98% Benign, 0.01% Infil | Recall @ Top 0.1% Anomaly Scores |
| **Test 5: Botnet** | Friday Morning | 98.9% Benign, 1.1% Bot | ROC-AUC, PR-AUC |
| **Test 6: PortScan** | Friday PortScan | 44.5% Benign, 55.5% PortScan | ROC-AUC, PR-AUC |
| **Test 7: DDoS** | Friday DDoS | 43.3% Benign, 56.7% DDoS | ROC-AUC, PR-AUC |

---

## 7. Isolation Forest Readiness Verdict: 🟢 FULLY READY FOR MODELING
The dataset suite satisfies all prerequisites for Isolation Forest experimentation once the deterministic preprocessing pipeline (deduplication, constant removal, log transform, inf imputation) is applied.
