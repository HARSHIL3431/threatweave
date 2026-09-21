# CICIDS2017 Feature Selection Decisions — Final Audit

## 1. Mandatory Removals

### 1.1 Constant Features (Zero Variance)

These 8 features are constant zero across all 2,830,743 rows. They provide zero isolation capability for Isolation Forest and zero information for any model.

| Feature | Unique Value | Evidence |
|:---|:---|:---|
| `Bwd PSH Flags` | 0 | Constant across all 2.83M rows |
| `Bwd URG Flags` | 0 | Constant across all 2.83M rows |
| `Fwd Avg Bytes/Bulk` | 0 | Constant across all 2.83M rows |
| `Fwd Avg Packets/Bulk` | 0 | Constant across all 2.83M rows |
| `Fwd Avg Bulk Rate` | 0 | Constant across all 2.83M rows |
| `Bwd Avg Bytes/Bulk` | 0 | Constant across all 2.83M rows |
| `Bwd Avg Packets/Bulk` | 0 | Constant across all 2.83M rows |
| `Bwd Avg Bulk Rate` | 0 | Constant across all 2.83M rows |

**Action**: REMOVE unconditionally.

### 1.2 Semi-Constant Features

| Feature | Non-Zero Count | Source | Verdict |
|:---|---:|:---|:---|
| `Fwd URG Flags` | 315 | Thursday-Afternoon Benign | **EXPERIMENT REQUIRED** |
| `CWE Flag Count` | 315 | Thursday-Afternoon Benign | **REMOVE** (duplicate of Fwd URG Flags, r=1.0) |
| `RST Flag Count` | ~670 | Mixed | **EXPERIMENT REQUIRED** |
| `ECE Flag Count` | ~670 | Mixed | **REMOVE** (duplicate of RST Flag Count, r=1.0) |

**Rationale for Fwd URG Flags**: While nearly constant (99.99%), the 315 non-zero activations in Thursday Afternoon Benign traffic may represent a specific network behavior pattern. However, with only 315/2,830,743 non-zero values, the signal is extremely weak.

**Recommendation**: Remove `CWE Flag Count` and `ECE Flag Count` (duplicates). Retain `Fwd URG Flags` and `RST Flag Count` as candidates for experimental removal.

### 1.3 Duplicate Column (Already Removed)

`Fwd Header Length.1` (column index 34) was already removed during integration. Verified: not present in combined dataset.

---

## 2. Redundant Feature Removal (r ≥ 0.999)

### 2.1 Redundancy Groups with Canonical Representatives

| Group | Features | Relationship | Retained | Removed | Reason |
|:---|:---|:---|:---|:---|:---|
| 1 | Total Fwd Packets, Subflow Fwd Packets, Total Length of Bwd Packets, Subflow Bwd Bytes | r = 1.000 | **Total Fwd Packets** | Subflow Fwd Packets, Total Length of Bwd Packets, Subflow Bwd Bytes | Total Fwd Packets is the most interpretable canonical form |
| 2 | Total Backward Packets, Subflow Bwd Packets | r = 1.000 | **Total Backward Packets** | Subflow Bwd Packets | Direct count is more interpretable |
| 3 | Total Length of Fwd Packets, Subflow Fwd Bytes | r = 1.000 | **Total Length of Fwd Packets** | Subflow Fwd Bytes | Original metric, not subflow-derived |
| 4 | Fwd Packet Length Mean, Avg Fwd Segment Size | r = 1.000 | **Fwd Packet Length Mean** | Avg Fwd Segment Size | Mean packet length is standard terminology |
| 5 | Bwd Packet Length Mean, Avg Bwd Segment Size | r = 1.000 | **Bwd Packet Length Mean** | Avg Bwd Segment Size | Mean packet length is standard terminology |
| 6 | Fwd PSH Flags, SYN Flag Count | r = 1.000 | **Fwd PSH Flags** | SYN Flag Count | PSH flag is the canonical TCP flag |
| 7 | Fwd URG Flags, CWE Flag Count | r = 1.000 | **Fwd URG Flags** | CWE Flag Count | URG flag is the canonical TCP flag |
| 8 | Fwd Header Length, Bwd Header Length | r = 0.999 | **Fwd Header Length** | Bwd Header Length | Forward header length is primary |
| 9 | RST Flag Count, ECE Flag Count | r = 1.000 | **RST Flag Count** | ECE Flag Count | RST is the standard TCP flag |

### 2.2 Features Removed (Total: 13)

From redundancy removal:
1. Subflow Fwd Packets
2. Subflow Bwd Packets
3. Subflow Fwd Bytes
4. Subflow Bwd Bytes
5. Avg Fwd Segment Size
6. Avg Bwd Segment Size
7. SYN Flag Count
8. CWE Flag Count
9. Bwd Header Length
10. ECE Flag Count

From constant removal (8):
11. Bwd PSH Flags
12. Bwd URG Flags
13. Fwd Avg Bytes/Bulk
14. Fwd Avg Packets/Bulk
15. Fwd Avg Bulk Rate
16. Bwd Avg Bytes/Bulk
17. Bwd Avg Packets/Bulk
18. Bwd Avg Bulk Rate

**Total features removed**: 18 (8 constant + 10 redundant)
**Remaining features**: 77 - 18 = **59 features**

---

## 3. Destination Port — Experimental Feature

### 3.1 Evidence

| Attack Type | Destination Port | Association Strength |
|:---|---:|:---|
| FTP-Patator | 21 | 100.0% |
| SSH-Patator | 22 | 100.0% |
| DoS (Hulk, GoldenEye, slowloris, Slowhttptest) | 80 | 100.0% |
| DDoS | 80 | 100.0% |
| Web Attacks | 80 | 100.0% |
| Heartbleed | 444 | 100.0% |
| Infiltration | 444 | 100.0% |
| Bot | 8080 | 64.1% |
| PortScan | Various | Distributed across 1,000 ports |

### 3.2 Risk Assessment

**Port Memorization Risk**: HIGH. If Destination Port is included, the model can learn a near-perfect lookup table: "Port 21 = FTP-Patator, Port 22 = SSH-Patator, Port 80 = DoS/DDoS." This is not behavioral anomaly detection — it is port-based classification.

**Behavioral Information Value**: MODERATE. Port numbers do carry legitimate information about which service is being targeted, which is relevant for real IDS deployment.

### 3.3 Recommendation

**EXPERIMENT REQUIRED** — Run Isolation Forest with and without Destination Port. Compare:
- False positive rate
- Attack-wise recall
- Whether the model learns port-based shortcuts vs. behavioral anomalies

**Primary model**: WITHOUT Destination Port (behavioral detection).
**Ablation model**: WITH Destination Port (for comparison).

---

## 4. Features with Negative Values (Transformation Impact)

12 features contain negative values, which prevents naive `log1p(x)` transformation:

| Feature | Minimum Value | Negative Count | Implication |
|:---|---:|---:|:---|
| Fwd Header Length | -32,212,234,632 | 35 | CICFlowMeter artifact |
| Bwd Header Length | -1,073,741,320 | 22 | CICFlowMeter artifact |
| min_seg_size_forward | -536,870,661 | 35 | CICFlowMeter artifact |
| Flow Bytes/s | -261,000,000 | ~variable | Negative byte rates |
| Flow Packets/s | -2,000,000 | ~variable | Negative packet rates |
| Flow Duration | -13 | ~variable | Negative durations |
| Flow IAT Mean | -13 | ~variable | Negative inter-arrival times |
| Flow IAT Max | -13 | ~variable | Negative IAT |
| Flow IAT Min | -14 | ~variable | Negative IAT |
| Fwd IAT Min | -12 | ~variable | Negative IAT |
| Init_Win_bytes_forward | -1 | ~variable | TCP window size artifact |
| Init_Win_bytes_backward | -1 | ~variable | TCP window size artifact |

**Critical implication**: `np.log1p(x)` is undefined for x < -1. Applying it to these features would produce NaN/complex values. The transformation strategy must handle this.

---

## 5. Final Feature Matrix Specification

**Starting features**: 77 numeric columns
**Removed (constant)**: 8 features
**Removed (redundant)**: 10 features
**Added (new)**: 1 feature (`Is_Zero_Duration`)
**Experimental**: 1 feature (`Destination Port`)

**Base feature count**: 77 - 18 + 1 = **60 features**
**With Destination Port**: 60 features (port is included by default)
**Without Destination Port (E1)**: 76 - 18 + 1 = **59 features** (port removed before dedup)
