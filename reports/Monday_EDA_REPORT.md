# Dataset 1: Monday-WorkingHours EDA Report

## 1. Dataset Overview
- **File**: `Monday-WorkingHours.pcap_ISCX.csv`
- **File Size**: 168.73 MB
- **Total Records**: 529,918
- **Total Columns**: 79 (78 distinct features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~319.1 MB in-memory
- **Intended Role**: Pure Benign Baseline representing normal enterprise working hours network activity.

---

## 2. Validation Status: PASS
- **Row Count Verification**: 529,918 flows present (valid volume).
- **Label Integrity**: 100% BENIGN. No corrupted or unlabeled records.
- **Parsing Validity**: Valid CSV parsing under Latin-1 / UTF-8.

---

## 3. Data Quality & Anomalies
- **Missing Values (NaN)**: 64 records in `Flow Bytes/s` (0.012%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 437 records
  - `Flow Bytes/s`: 373 records
  - **Root Cause**: 100.0% (437/437) of Inf records have `Flow Duration == 0`. In CICFlowMeter, flow rates are computed as `Count / Flow Duration`, producing mathematical division by zero.
- **Duplicate Records**: 26,935 rows (5.08%).
- **Constant Zero-Variance Features (10)**:
  `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.

---

## 4. Label Distribution
| Label | Count | Percentage | Classification |
| :--- | :--- | :--- | :--- |
| `BENIGN` | 529,918 | 100.00% | Normal Background Traffic |

---

## 5. Feature Statistics & Distributions
- **Flow Duration**: Highly bimodal/skewed. 
  - 5th percentile: 3 µs (fast single-packet / DNS queries)
  - Median: 31,303 µs (~31.3 ms)
  - 95th percentile: 102.2 seconds (persistent long TCP streams)
  - Maximum: 120.0 seconds (CICFlowMeter default flow timeout)
- **Flow Directionality**:
  - Bidirectional Flows: 452,602 (85.41%)
  - Forward-Only Flows (Unidirectional / No Reply): 77,316 (14.59%)
  - Backward-Only: 0

---

## 6. Cybersecurity & Network Behavioral Findings
- **Dominant Services & Protocols**:
  - Port 53 (DNS): 40.51% (214,674 flows) — standard short UDP query/response.
  - Port 443 (HTTPS): 26.60% (140,952 flows) — encrypted web traffic.
  - Port 80 (HTTP): 9.59% (50,834 flows) — cleartext web traffic.
  - Port 123 (NTP): 0.98% (5,180 flows) — network time synchronization.
  - Port 22 (SSH): 0.40% (2,132 flows) — normal administrative access.
- **Stability of Benign Profile**: Monday establishes the ground-truth baseline for standard enterprise workloads. Any attack detection model must avoid flagging high-frequency DNS or long HTTPS idle streams as anomalies.

---

## 7. Outlier Findings
- **Extreme Flow Durations (>100s)**: Represent legitimate sustained TCP downloads or long-lived idle sessions rather than malicious DoS activity.
- **Extreme Packet Lengths (Max = 9,504 bytes)**: Represent Jumbo Ethernet frames / TCP segmentation offload (TSO) on the local enterprise network.
- **Recommendation**: Do not blindly truncate or clip extreme values; use robust scaling (Median / IQR) during modeling.

---

## 8. Infinite-Value Findings
| Feature | Inf Count | Root Cause | Affected Label | Preprocessing Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `Flow Packets/s` | 437 | `Flow Duration == 0` (Zero denominator) | BENIGN (100%) | Replace with max observed valid rate or impute `Packets / 1.0 µs` |
| `Flow Bytes/s` | 373 | `Flow Duration == 0` & `Total Bytes > 0` | BENIGN (100%) | Replace with max observed valid rate or impute `Bytes / 1.0 µs` |

---

## 9. Correlation & Redundancy Findings
63 feature pairs exhibit Pearson correlation $|r| \ge 0.90$. Exact mathematical duplicates ($r = 1.0000$) include:
1. `Bwd Packet Length Mean` $\equiv$ `Avg Bwd Segment Size`
2. `Fwd Packet Length Mean` $\equiv$ `Avg Fwd Segment Size`
3. `Fwd Header Length` $\equiv$ `Fwd Header Length.1`
4. `Fwd PSH Flags` $\equiv$ `SYN Flag Count`
5. `Total Fwd Packets` $\equiv$ `Subflow Fwd Packets`
6. `Total Backward Packets` $\equiv$ `Subflow Bwd Packets`
7. `Total Length of Fwd Packets` $\equiv$ `Subflow Fwd Bytes`
8. `Total Length of Bwd Packets` $\equiv$ `Subflow Bwd Bytes`

---

## 10. Key Visualizations
- `figures/monday/monday_top_destination_ports.png`: Distribution of top 10 destination ports.
- `figures/monday/monday_flow_duration_log_dist.png`: Bimodal log-duration distribution.
- `figures/monday/monday_packet_length_vs_byte_rate.png`: Relationship between packet size and throughput.
- `figures/monday/monday_key_features_correlation.png`: Heatmap of key flow feature correlations.

---

## 11. Preprocessing Implications
1. **Drop duplicate column index 34 (`Fwd Header Length.1`)**.
2. **Drop 10 zero-variance constant features**.
3. **Handle 64 NaN and 437 Inf values deterministically** before feeding into models.
4. **Deduplicate or stratify** to mitigate the 5.08% duplicate record leakage risk.

---

## 12. ML & Isolation Forest Readiness: 🟢 READY
Monday provides a clean, well-characterized 100% benign dataset ideal for training unsupervised anomaly detectors (Isolation Forest, One-Class SVM) to establish the normal enterprise baseline.
