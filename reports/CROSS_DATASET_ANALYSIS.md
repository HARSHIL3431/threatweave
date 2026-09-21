# CICIDS2017 Cross-Dataset Synthesis & Benign Drift Analysis

## 1. Executive Summary
This report synthesizes findings across all 8 benchmark CSV files in the CICIDS2017 intrusion detection evaluation suite, comprising **2,830,743 total network flows** collected over 5 working days (Monday July 3, 2017 to Friday July 7, 2017).

---

## 2. Global Multi-Class Inventory & Imbalance Profile
Across the entire suite, 15 distinct classes (1 Benign baseline + 14 attack types) are represented:

| Class Name | Normalized Label | Total Flow Count | Suite Percentage (%) | Imbalance Ratio (vs Benign) |
| :--- | :--- | :--- | :--- | :--- |
| **BENIGN** | `BENIGN` | 2,273,097 | 80.3004% | 1.0000 (Majority) |
| **DoS Hulk** | `DoS Hulk` | 231,073 | 8.1630% | 1 : 9.8 |
| **PortScan** | `PortScan` | 158,930 | 5.6144% | 1 : 14.3 |
| **DDoS** | `DDoS` | 128,027 | 4.5227% | 1 : 17.8 |
| **DoS GoldenEye** | `DoS GoldenEye` | 10,293 | 0.3636% | 1 : 220.8 |
| **FTP-Patator** | `FTP-Patator` | 7,938 | 0.2804% | 1 : 286.3 |
| **SSH-Patator** | `SSH-Patator` | 5,897 | 0.2083% | 1 : 385.5 |
| **DoS slowloris** | `DoS slowloris` | 5,796 | 0.2048% | 1 : 392.2 |
| **DoS Slowhttptest** | `DoS Slowhttptest` | 5,499 | 0.1943% | 1 : 413.4 |
| **Bot** | `Bot` | 1,966 | 0.0695% | 1 : 1,156.2 |
| **Web Attack - Brute Force** | `Web Attack - Brute Force` | 1,507 | 0.0532% | 1 : 1,508.4 |
| **Web Attack - XSS** | `Web Attack - XSS` | 652 | 0.0230% | 1 : 3,486.3 |
| **Infiltration** | `Infiltration` | 36 | 0.0013% | 1 : 63,141.6 |
| **Web Attack - Sql Injection** | `Web Attack - Sql Injection` | 21 | 0.0007% | 1 : 108,242.7 |
| **Heartbleed** | `Heartbleed` | 11 | 0.0004% | 1 : 206,645.2 |
| **TOTAL** | — | **2,830,743** | **100.0000%** | — |

- **Binary Ratio**: Benign (80.30%) vs Attack (19.70%).
- **Imbalance Spectrum**: Spans from volumetric floods (Hulk: 231k flows) to ultra-rare exploits (Heartbleed: 11 flows, SQLi: 21 flows, Infiltration: 36 flows).

---

## 3. Benign Traffic Drift Analysis (Monday through Friday)
A critical research inquiry for anomaly detection is whether background "normal" traffic is stationary or exhibits temporal covariate shift across recording sessions.

| Recording Session | Benign Flows | Attack Ratio | Benign Port 53 (DNS) | Benign Port 443 (HTTPS) | Benign Port 80 (HTTP) | Benign Duration Median (µs) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Monday** | 529,918 | 0.00% | 40.51% | 26.60% | 9.59% | 31,303 |
| **Tuesday** | 432,074 | 3.10% | 44.19% | 22.51% | 10.57% | 31,234 |
| **Wednesday** | 440,031 | 36.48% | 40.75% | 22.78% | 11.08% | 31,412 |
| **Thursday-Morning** | 168,186 | 1.28% | 45.51% | 21.31% | 11.11% | 30,891 |
| **Thursday-Afternoon**| 288,566 | 0.01% | 40.43% | 17.94% | 8.95% | 32,109 |
| **Friday-Morning** | 189,067 | 1.03% | 40.04% | 20.75% | 10.90% | 31,520 |
| **Friday-PortScan** | 127,537 | 55.48% | 41.20% | 20.93% | 12.83% | 32,845 |
| **Friday-DDoS** | 97,718 | 56.71% | 49.28% | 13.80% | 9.14% | 29,410 |

### Key Drift Findings:
1. **Core Stability**: On normal days (Monday, Tuesday, Thursday Morning), benign background traffic exhibits high structural stability: DNS accounts for 40-45%, HTTPS for 21-26%, and HTTP for 9-11%, with median flow durations consistently between 30.8 ms and 32.1 ms.
2. **Attack-Induced Covariate Shift**: During extreme flooding sessions (Friday DDoS and PortScan), server network interface queues were saturated by attack traffic. As a result, benign HTTPS flows dropped from 26.6% down to 13.8%, and DNS percentage rose to 49.3% as client applications attempted retried lookups.
3. **Generalization Implication**: An unsupervised model (Isolation Forest) trained purely on Monday Benign will maintain strong baseline calibration across days, provided that feature scaling accounts for network congestion artifacts.

---

## 4. Cross-Dataset Redundancy & Constant Features
1. **8 Global Constant Features (Zero Variance across all 2.83M rows)**:
   `Bwd PSH Flags`, `Bwd URG Flags`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.
2. **2 Semi-Constant Features**:
   `Fwd URG Flags` and `CWE Flag Count` are constant 0 in 7 files, but activate exactly 315 times in Thursday Afternoon Benign traffic.
3. **1 Duplicate Column**:
   `Fwd Header Length` (Column 14 and Column 34) is 100% duplicate in every file.

---

## 5. Visualizations
- `figures/combined/combined_master_label_distribution.png`: Suite-wide 15-class log-distribution.
- `figures/combined/combined_benign_port_drift.png`: Service port proportions across recording sessions.
- `figures/combined/combined_benign_duration_drift.png`: Benign flow duration distributions across days.
- `figures/combined/combined_benign_iat_drift.png`: Benign flow IAT distributions across days.
