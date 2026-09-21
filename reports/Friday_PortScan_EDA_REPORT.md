# Dataset 7: Friday-WorkingHours-Afternoon-PortScan EDA Report

## 1. Dataset Overview
- **File**: `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
- **File Size**: 73.34 MB
- **Total Records**: 286,467
- **Total Columns**: 79 (78 features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~172.5 MB in-memory
- **Intended Attack Scenario**: Port Scanning (Reconnaissance scanning of network services across target host ports).

---

## 2. Validation Status: PASS
- **Row Count Verification**: 286,467 rows loaded cleanly.
- **Attack Class Presence**: 158,930 confirmed `PortScan` flows (55.48%).
- **Label Integrity**: 100% valid string labels.

---

## 3. Data Quality & Anomalies: High Duplicate Rate Investigation
- **Missing Values (NaN)**: 15 records in `Flow Bytes/s` (0.005%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 371 records (245 BENIGN, 126 PortScan)
  - `Flow Bytes/s`: 356 records
  - **Root Cause**: 100% (371/371) of Inf records have `Flow Duration == 0`.
- **Severe Duplicate Rate (25.26%)**:
  - Total Duplicates: 72,353 rows (25.26%).
  - **Within PortScan Class**: **68,111 / 158,930 records (42.86%)** are exact duplicates!
  - **Cybersecurity Root Cause**: 99.07% of PortScan flows consist of identical 1-packet TCP probe attempts (`Total Fwd Packets == 1`, `Total Backward Packets == 1`, `Fwd Header Length == 32`, zero payload). When Nmap sweeps the top 1,000 ports, identical packet templates generate identical flow vectors.
- **Constant Zero-Variance Features (10)**:
  `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.

---

## 4. Label Distribution
| Class Label | Count | Percentage | Class Ratio (vs Majority) |
| :--- | :--- | :--- | :--- |
| `PortScan` | 158,930 | 55.4793% | 1.2461 (Majority) |
| `BENIGN` | 127,537 | 44.5207% | 1.0000 |

Total PortScan Traffic: 158,930 flows (55.48%).

---

## 5. Cybersecurity & Network Behavioral Findings
### A. Destination Port Spectrum
- PortScan systematically probed **exactly 1,000 distinct destination ports** (matching Nmap's default `--top-ports 1000` scanning profile across well-known and registered services).
- Benign traffic targeted standard working ports (53, 443, 80, etc.).

### B. Flow Mechanics & Behavioral Fingerprint
- **Dominance of 1-Packet Probes**: 99.07% (157,448 / 158,930) of all PortScan records contain exactly 1 forward packet.
- **TCP PSH Flag Concentration**: 99.96% of PortScan records have `PSH Flag Count == 1` in the flow record.
- **Extremely Low Flow Duration**: Median duration is negligible (a few microseconds per probe).

---

## 6. Key Visualizations
- `figures/friday_portscan/friday_portscan_label_distribution.png`: Balanced class distribution.
- `figures/friday_portscan/friday_portscan_port_spectrum.png`: Port spectrum showing broad horizontal/vertical scanning.
- `figures/friday_portscan/friday_portscan_duration_comparison.png`: Comparison showing microsecond probe durations in PortScan.
- `figures/friday_portscan/friday_portscan_1pkt_probes.png`: Prevalence of 1-packet probe flows.

---

## 7. Preprocessing & ML Readiness Implications
1. **Critical Leakage Risk via Duplicates**: If PortScan is randomly split into train/test without deduplication, over 42.8% of test port scan records will be identical clones of training records, resulting in falsely inflated 99.99% test accuracies. Deduplication is mandatory.
2. **Feature Pruning**: Features derived from multi-packet streams (e.g. `Bwd Packet Length Std`, `Flow IAT Mean`) are trivial zeros for single-packet scan flows.

---

## 8. ML & Isolation Forest Readiness: 🟢 READY
PortScan produces a compact, tightly clustered geometric anomaly signature distinct from benign traffic.
