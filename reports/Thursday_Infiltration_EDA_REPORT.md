# Dataset 5: Thursday-WorkingHours-Afternoon-Infilteration EDA Report

## 1. Dataset Overview
- **File**: `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`
- **File Size**: 79.25 MB
- **Total Records**: 288,602
- **Total Columns**: 79 (78 features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~173.8 MB in-memory
- **Intended Attack Scenario**: Network Infiltration involving multi-stage compromise (reconnaissance, vulnerability exploitation, backdoor installation, and command delivery).

---

## 2. Validation Status: PASS
- **Row Count Verification**: 288,602 rows present.
- **Attack Class Presence**: 36 confirmed `Infiltration` flows.
- **Label Integrity**: 100% valid string labels.

---

## 3. Data Quality & Anomalies
- **Missing Values (NaN)**: 18 records in `Flow Bytes/s` (0.006%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 207 records
  - `Flow Bytes/s`: 189 records
  - **Root Cause**: 100% (207/207) of Inf records have `Flow Duration == 0` in background benign traffic.
- **Duplicate Records**: 35,630 rows (12.35%).
- **Constant vs Activated Flags**:
  - Across most other days, `Fwd URG Flags` and `CWE Flag Count` are constant 0.
  - In this dataset, both features have exactly **315 non-zero activations** (100% co-occurring in background BENIGN traffic, 0 in Infiltration).

---

## 4. Label Distribution & Extreme Rarity
| Class Label | Count | Percentage | Class Ratio (vs Majority) |
| :--- | :--- | :--- | :--- |
| `BENIGN` | 288,566 | 99.9875% | 1.0000 (Majority) |
| `Infiltration` | 36 | 0.0125% | 1 : 8,015.7 |

Total Attack Traffic: 36 flows (0.0125%).

---

## 5. Cybersecurity & Network Behavioral Findings
### A. Destination Port Targeting
- **100.0% of Infiltration flows (36 records)** targeted **Destination Port 444** (Custom backdoor listener port).
- Background benign traffic targeted Port 53 (DNS, 116,664 flows), Port 443 (HTTPS, 62,398 flows), and Port 80 (HTTP, 38,154 flows).

### B. Infiltration Flow Dynamics
- **Long-Lived Command Sessions**:
  - Median Flow Duration is **93.2 seconds** (Mean: 78.4 seconds, Max: 120.0 seconds).
  - Contrasts sharply with transient benign web/DNS queries.
- **Symmetric Packet Counts**:
  - Flows exhibit highly structured, symmetric packet counts (Median: **26 Forward packets and 26 Backward packets**).
- **Asymmetric Payload Sizes**:
  - Forward Packet Length Mean: **296.87 bytes** (containing shell commands and exploit code sent to victim).
  - Backward Packet Length Mean: **7.04 bytes** (minimal acknowledgement / execution status bytes returned from victim).

---

## 6. Key Visualizations
- `figures/thursday_infiltration/thursday_infiltration_label_distribution.png`: Extreme class imbalance illustration.
- `figures/thursday_infiltration/thursday_infiltration_ports.png`: Port 444 concentration of all 36 Infiltration flows.
- `figures/thursday_infiltration/thursday_infiltration_duration_comparison.png`: Boxplot showing persistent flow duration in Infiltration.

---

## 7. Preprocessing & ML Readiness Implications
1. **Extreme Imbalance Handling**: 36 instances are insufficient for standard stratified 80/20 train/test splits. Unsupervised anomaly detection (Isolation Forest) trained on pure benign traffic (Monday) is the most methodologically sound approach for evaluating Infiltration detection.
2. **Port 444 Leakage Risk**: Models trained with `Destination Port` may overfit to port 444 rather than learning the payload size asymmetry (296B fwd vs 7B bwd) and persistent flow duration.

---

## 8. ML & Isolation Forest Readiness: 🟢 READY
The dataset offers an authentic benchmark for ultra-rare anomaly detection.
