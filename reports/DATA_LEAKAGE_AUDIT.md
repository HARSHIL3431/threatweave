# CICIDS2017 Data Leakage Audit Report

## 1. Executive Summary
Data leakage is one of the most severe pitfalls in machine learning for network intrusion detection. In benchmark evaluations of CICIDS2017, many published studies report unrealistically high detection rates (>99.9% F1-score) because of unaddressed structural, duplicate, and contextual leakage channels. This audit identifies and categorizes all primary leakage vectors present in CICIDS2017 with actionable mitigation strategies.

---

## 2. Duplicate Flow Leakage (Critical Severity)
- **Observed Evidence**:
  - Across all 8 datasets, **255,446 exact duplicate flow records** exist (9.02% suite-wide).
  - On specific attack subsets, duplicate rates are extreme:
    - **PortScan**: 42.86% of all PortScan attack flows (68,111 / 158,930) are identical.
    - **DoS Hulk**: 11.82% duplicates due to repeated HTTP GET template emissions.
    - **Infiltration**: 12.35% duplicates.
- **Leakage Mechanism**:
  - Standard random train/test splitting (e.g., `train_test_split(test_size=0.2, random_state=42)`) distributes duplicate flows into both train and test partitions.
  - The model memorizes exact feature coordinates seen in training, artificially inflating test accuracy and masking genuine generalization failure.
- **Mitigation Requirement**:
  - Apply strict deduplication prior to partitioning, or implement grouped/session-based partitioning where duplicate clusters remain confined to a single fold.

---

## 3. Destination Port & Environmental Artifact Leakage (High Severity)
- **Observed Evidence**:
  - `FTP-Patator`: 99.99% targeted Port 21.
  - `SSH-Patator`: 100.0% targeted Port 22.
  - `DoS (Hulk, GoldenEye, slowloris, Slowhttptest)`: 100.0% targeted Port 80.
  - `Heartbleed` & `Infiltration`: 100.0% targeted Port 444.
  - `Web Attacks`: 100.0% targeted Port 80.
- **Leakage Mechanism**:
  - Because testbed attacks were directed at specific services on predefined testbed servers, decision trees and deep models frequently select `Destination Port` at root split points.
  - The classifier learns a lookup table of port numbers rather than behavioral network dynamics (such as request rates, payload asymmetry, or TCP flag anomalies).
- **Mitigation Requirement**:
  - For domain-invariant anomaly detection, models should exclude `Destination Port` or evaluate models with and without port features to benchmark true behavioral detection.

---

## 4. Temporal & Burst Leakage (High Severity)
- **Observed Evidence**:
  - Attacks in CICIDS2017 occurred during specific scheduled execution windows (e.g., PortScan was run during Friday afternoon; Web Attacks were executed Thursday morning).
  - Consecutive flows in an attack burst share correlated timing features (`Flow IAT`, `Active/Idle` states).
- **Leakage Mechanism**:
  - Random shuffle-splitting samples flows from within the same continuous multi-minute attack burst into both train and test sets.
- **Mitigation Requirement**:
  - Use time-contiguous block splitting (e.g., train on first 60% of an attack timeline, test on final 40%) or cross-day evaluation (train normal baseline on Monday, test on Tuesday–Friday).

---

## 5. Preprocessing & Transformation Leakage (Medium Severity)
- **Observed Evidence**:
  - `Flow Bytes/s` and `Flow Packets/s` contain extreme outliers, infinite values (+Inf), and missing values (NaN).
- **Leakage Mechanism**:
  - Fitting standardizers (e.g. `StandardScaler().fit(X_all)`), imputers, or clipping percentiles over the full 2.83M records leaks test-set distribution moments (mean, std, max) into training.
- **Mitigation Requirement**:
  - Encapsulate all imputation, inf-handling, and scaling within an explicit `Pipeline` fitted **exclusively on training data**.

---

## 6. Summary of Leakage Vectors & Mitigation Matrix

| Leakage Channel | Severity | Root Cause in CICIDS2017 | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Duplicate Flows** | `CRITICAL` | Single-packet Nmap scans and repeated DoS flood templates | Deduplicate prior to train/test split |
| **Port Memorization** | `HIGH` | Attacks targeted single static service ports (21, 22, 80, 444) | Evaluate behavioral models with `Destination Port` removed |
| **Temporal Bursts** | `HIGH` | Attack bursts concentrated in narrow timeframes | Time-based / Cross-day validation |
| **Global Preprocessing** | `MEDIUM` | Scaling/imputing on combined datasets | Strict Scikit-Learn `Pipeline` fitted on train fold only |
