# Dataset 3: Wednesday-workingHours EDA Report

## 1. Dataset Overview
- **File**: `Wednesday-workingHours.pcap_ISCX.csv`
- **File Size**: 214.74 MB
- **Total Records**: 692,703
- **Total Columns**: 79 (78 distinct features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~417.3 MB in-memory
- **Intended Attack Scenarios**: Denial of Service (DoS) attacks (Hulk, GoldenEye, slowloris, Slowhttptest) and the Heartbleed OpenSSL memory leak exploit.

---

## 2. Validation Status: PASS
- **Row Count Verification**: 692,703 rows loaded cleanly.
- **Attack Class Verification**: All 5 expected attack classes are present.
- **Label Integrity**: 100% valid string labels.

---

## 3. Data Quality & Anomalies
- **Missing Values (NaN)**: 1,008 records in `Flow Bytes/s` (0.145%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 1,297 records (949 in `DoS Hulk`, 348 in `BENIGN`)
  - `Flow Bytes/s`: 289 records
  - **Root Cause**: 100.0% (1,297/1,297) of Inf records have `Flow Duration == 0`. Rapid DoS flood packet bursts timestamped identically produce zero-duration flows.
- **Duplicate Records**: 81,909 rows (11.82%) — elevated duplicate rate caused by automated flooding scripts firing identical HTTP request templates.
- **Constant Zero-Variance Features (10)**:
  `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.

---

## 4. Label Distribution & Severe Imbalance
| Class Label | Count | Percentage | Class Ratio (vs Majority) | Attack Type |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | 440,031 | 63.52% | 1.0000 (Majority) | Normal background traffic |
| `DoS Hulk` | 231,073 | 33.36% | 1 : 1.90 | Volumetric Application-Layer Flooding |
| `DoS GoldenEye` | 10,293 | 1.49% | 1 : 42.7 | Multi-threading HTTP Keep-Alive Flooding |
| `DoS slowloris` | 5,796 | 0.84% | 1 : 75.9 | Slow-and-low HTTP Header Starvation |
| `DoS Slowhttptest` | 5,499 | 0.79% | 1 : 80.0 | Slow-and-low Incomplete HTTP Request |
| `Heartbleed` | 11 | 0.0016% | 1 : 40,003 | SSL/TLS Memory Leak Exploit (CVE-2014-0160) |

Total Attack Traffic: 252,672 flows (36.48%).

---

## 5. Cybersecurity & Network Behavioral Findings
### A. Destination Port Targeting
- **100% of DoS Attacks (Hulk, GoldenEye, slowloris, Slowhttptest)** targeted **Port 80** (HTTP Web Server).
- **100% of Heartbleed flows (11 records)** targeted **Port 444** (Custom vulnerable OpenSSL TLS server port).

### B. Volumetric Flooding vs Slow-and-Low DoS Mechanics
1. **DoS Hulk & GoldenEye (Volumetric Flooding)**:
   - High traffic intensity with massive flow generation (Hulk alone accounts for 231,073 flows).
   - Generates numerous single-packet / zero-duration bursts (accounting for 949 infinite packet rate records).
2. **DoS Slowloris & Slowhttptest (Resource Exhaustion)**:
   - Designed to exhaust web server connection pools by sending periodic keep-alive headers while never completing the HTTP request.
   - For `DoS Slowhttptest`, the **median Backward Packets is exactly 0** (unidirectional request starvation; server connection is tied up without returning HTTP responses).
   - Long inter-arrival times (Flow IAT) designed specifically to evade simple rate-based firewalls.
3. **Heartbleed Exploit Profile (11 Flows)**:
   - Characterized by long-duration SSL connections (Mean duration: **110.7 seconds**).
   - Heavy data exfiltration: Average of **2,583 forward packets** triggering **1,897 backward packets**, exfiltrating an average of **7.28 MB of unencrypted process memory** per flow.

---

## 6. Outlier & Feature Dynamics
- Heartbleed records are extreme statistical outliers in backward packet length (7.28 MB vs standard benign median of 136 bytes).
- DoS Hulk produces extreme outliers in flow arrival rate and burst counts.

---

## 7. Infinite-Value Findings
| Feature | Inf Count | Root Cause | Affected Label | Preprocessing Recommendation |
| :--- | :--- | :--- | :--- | :--- |
| `Flow Packets/s` | 1,297 | `Flow Duration == 0` | DoS Hulk (949), BENIGN (348) | Impute using duration of 1 µs or upper bound |
| `Flow Bytes/s` | 289 | `Flow Duration == 0` & `Bytes > 0` | DoS Hulk (241), BENIGN (48) | Impute using duration of 1 µs or upper bound |

---

## 8. Key Visualizations
- `figures/wednesday/wednesday_label_distribution.png`: Log-scale class distribution across all DoS types.
- `figures/wednesday/wednesday_flow_duration_dos_comparison.png`: Comparison of flow durations highlighting long-lived slow DoS vs short flooding.
- `figures/wednesday/wednesday_flow_iat_mean_comparison.png`: Inter-arrival time profiles distinguishing Slowloris.
- `figures/wednesday/wednesday_heartbleed_profile.png`: Structural profile of Heartbleed memory exfiltration.

---

## 9. Preprocessing & ML Readiness Implications
1. **Heartbleed Evaluation Strategy**: With only 11 total instances, random train/test splitting risks having 0 Heartbleed samples in test or train folds. Stratified K-fold or leave-one-group-out validation is mandatory.
2. **Duplication Impact**: 11.82% duplicate rate (81.9k rows) is dominated by repeated Hulk requests. Deduplication is essential to prevent inflated test accuracy.
3. **Port 80 Redundancy**: Because all DoS attacks target Port 80, classifiers must learn flow rate and timing features rather than relying on destination port.

---

## 10. ML & Isolation Forest Readiness: 🟢 READY
Wednesday provides rich contrast between high-rate flooding, stealthy slow-and-low starvation, and memory exfiltration anomalies.
