# Dataset 2: Tuesday-WorkingHours EDA Report

## 1. Dataset Overview
- **File**: `Tuesday-WorkingHours.pcap_ISCX.csv`
- **File Size**: 128.82 MB
- **Total Records**: 445,909
- **Total Columns**: 79 (78 features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~268.7 MB in-memory
- **Intended Attack Scenarios**: Network Brute-Force Attacks targeting authentication services (FTP-Patator and SSH-Patator).

---

## 2. Validation Status: PASS
- **Row Count Verification**: 445,909 rows loaded successfully.
- **Attack Class Presence**: Both `FTP-Patator` (7,938 flows) and `SSH-Patator` (5,897 flows) confirmed present.
- **Label Integrity**: 100% valid string labels; no missing or corrupt labels.

---

## 3. Data Quality & Anomalies
- **Missing Values (NaN)**: 201 records in `Flow Bytes/s` (0.045%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 264 records
  - `Flow Bytes/s`: 63 records
  - **Root Cause**: 100% (264/264) of Inf records have `Flow Duration == 0`.
  - **Affected Labels**: 261 BENIGN records and 3 FTP-Patator records.
- **Duplicate Records**: 24,065 rows (5.40%).
- **Constant Zero-Variance Features (10)**:
  `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.

---

## 4. Label Distribution & Imbalance
| Class Label | Count | Percentage | Class Ratio (vs Majority) |
| :--- | :--- | :--- | :--- |
| `BENIGN` | 432,074 | 96.90% | 1.0000 (Majority) |
| `FTP-Patator` | 7,938 | 1.78% | 1 : 54.4 |
| `SSH-Patator` | 5,897 | 1.32% | 1 : 73.3 |

Total Attack Traffic: 13,835 flows (3.10%).

---

## 5. Cybersecurity & Network Behavioral Findings
### A. Targeted Services & Ports
- **FTP-Patator**: 99.99% (7,937 / 7,938) targeted Destination Port 21 (FTP Control).
- **SSH-Patator**: 100.0% (5,897 / 5,897) targeted Destination Port 22 (SSH Daemon).
- In contrast, legitimate background traffic on Tuesday primarily targeted Port 53 (DNS, 190,939 flows), Port 443 (HTTPS, 97,276 flows), and Port 80 (HTTP, 45,675 flows).

### B. Flow Signature & Protocol Mechanics
1. **FTP-Patator**:
   - Flows represent automated rapid dictionary attempts over unencrypted TCP streams.
   - Characterized by concise command exchanges (`USER <name>`, `PASS <pwd>`) followed immediately by server rejection (`530 Login incorrect`).
   - Median Backward Packet Length is exactly **76 bytes**, forming a distinct structural fingerprint.
2. **SSH-Patator**:
   - Flows involve full SSH version exchange, Diffie-Hellman cryptographic key negotiation, and public key/password authentication attempts.
   - Because cryptographic negotiation requires substantial key material exchange before rejection (`SSH_MSG_USERAUTH_FAILURE`), backward packet lengths are much larger (Median: **2,009 bytes** across 15-22 packets).

---

## 6. Outlier & Feature Dynamics
- High packet count outliers in SSH-Patator (>50 packets) correspond to multi-attempt persistent SSH sessions.
- Extreme flow durations in Benign traffic (>100 seconds) contrast sharply with rapid, automated Patator flows that typically complete within 1–5 seconds.

---

## 7. Infinite-Value Findings
| Feature | Inf Count | Root Cause | Affected Label | Preprocessing Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `Flow Packets/s` | 264 | `Flow Duration == 0` | BENIGN: 261, FTP-Patator: 3 | Replace with upper valid boundary or impute using 1 µs duration |
| `Flow Bytes/s` | 63 | `Flow Duration == 0` | BENIGN: 60, FTP-Patator: 3 | Replace with upper valid boundary or impute using 1 µs duration |

---

## 8. Key Visualizations
- `figures/tuesday/tuesday_label_distribution.png`: Log-scale class distribution.
- `figures/tuesday/tuesday_flow_duration_by_class.png`: Duration distributions highlighting fast Patator iterations.
- `figures/tuesday/tuesday_packet_symmetry.png`: Forward vs backward packet count scatter plot.
- `figures/tuesday/tuesday_fwd_pkt_length_density.png`: Kernel density of forward packet lengths.

---

## 9. Preprocessing & Modeling Implications
1. **Port Leakage Warning**: `Destination Port` separates 99.9% of attacks in this specific recording environment because attack tools were directed at fixed server IPs on standard ports (21 & 22). Models evaluated on datasets with Destination Port included may learn port numbers rather than behavioral traffic dynamics.
2. **Robust Scaling**: Significant variance between short FTP flows and heavy SSH flows necessitates robust scaling.
3. **Deduplication**: 5.40% duplicate rate requires train/test split hygiene to avoid memorization.

---

## 10. ML & Isolation Forest Readiness: 🟢 READY
Tuesday exhibits distinct brute-force cluster patterns with sufficient volume (13.8k attack flows) to benchmark both supervised classifiers and unsupervised anomaly detectors against high-frequency authentication attacks.
