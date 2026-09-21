# CICIDS2017 Comprehensive Exploratory Data Analysis Final Master Report

---

## 1. Executive Summary
This report presents the consolidated findings of an autonomous, iterative, and cybersecurity-focused Exploratory Data Analysis (EDA) conducted on the full **CICIDS2017 benchmark dataset suite**. The suite contains **8 distinct CSV files** encompassing **2,830,743 network flow records** across 5 working days (Monday through Friday), representing normal enterprise background activity alongside 14 network attack scenarios.

Rather than applying a generic tabular script, every dataset was investigated iteratively through actual Python execution, domain-specific network protocol interpretation, mathematical root-cause analysis of numerical anomalies, and systematic leakage audits.

**Key Suite Highlights**:
- **Total Suite Volume**: 2,830,743 flows (80.30% Benign, 19.70% Attack).
- **Attack Spectrum**: Spans volumetric floods (DoS Hulk: 231,073 flows) to extreme minority exploits (Heartbleed: 11 flows, SQL Injection: 21 flows, Infiltration: 36 flows).
- **Data Quality Anomalies**: Infinite values (+Inf) occur in 2 features (`Flow Bytes/s` and `Flow Packets/s`) and are mathematically caused by 0-duration flows ($100.0\%$ co-occurrence).
- **Critical Leakage Risk**: 255,446 duplicate rows exist (notably 42.86% within PortScan and 11.82% in DoS Hulk), necessitating deduplication to prevent inflated test metrics.
- **Master Verdict**: **🟢 READY FOR PREPROCESSING**.

---

## 2. Dataset Inventory
All 8 original CSV files located in `dataset/` were verified and cataloged with SHA-256 integrity checksums:

| Dataset Filename | Size (MB) | Total Rows | Columns | Classes | NaN Records | Inf Records | Duplicate Rows (%) | Constant Features | Validation Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Monday-WorkingHours.pcap_ISCX.csv` | 168.73 | 529,918 | 79 | 1 | 64 | 437 | 26,935 (5.08%) | 10 | **PASS** |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 128.82 | 445,909 | 79 | 3 | 201 | 264 | 24,065 (5.40%) | 10 | **PASS** |
| `Wednesday-workingHours.pcap_ISCX.csv` | 214.74 | 692,703 | 79 | 6 | 1,008 | 1,297 | 81,909 (11.82%) | 10 | **PASS** |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 49.61 | 170,366 | 79 | 4 | 20 | 135 | 6,066 (3.56%) | 10 | **WARNING** |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 79.25 | 288,602 | 79 | 2 | 18 | 207 | 35,630 (12.35%) | 8 | **PASS** |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 55.62 | 191,033 | 79 | 2 | 28 | 122 | 6,888 (3.61%) | 10 | **PASS** |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 73.34 | 286,467 | 79 | 2 | 15 | 371 | 72,353 (25.26%) | 10 | **PASS** |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 73.55 | 225,745 | 79 | 2 | 4 | 34 | 2,633 (1.17%) | 10 | **PASS** |
| **TOTAL / SUITE** | **869.66 MB** | **2,830,743** | **79** | **15** | **1,358** | **2,867** | **255,446 (9.02%)** | — | — |

---

## 3. Dataset Validation Findings
1. **Schema Consistency**: Every file contains exactly 79 raw columns. However, column index 34 contains an exact duplicate of column index 14 (`Fwd Header Length`). This redundancy is identical across all files.
2. **Whitespace Header Inconsistency**: 64 out of 79 column names contain leading spaces (e.g. `' Flow Duration'`).
3. **Label Encoding Anomaly on Thursday Morning**:
   - Attack strings in Thursday Web Attacks contain Windows-1252 byte `0x96` (en-dash `–`), which standard UTF-8 decoders interpret as `\ufffd` (`ï¿½`).
   - Explicit string sanitization is required (`'Web Attack \x96 Brute Force'` $\rightarrow$ `'Web Attack - Brute Force'`).

---

## 4. Data Quality Findings
- **Missing Values (NaN)**: Across all 2,830,743 records, `NaN` occurs in exactly **one feature**: `Flow Bytes/s` (total 1,358 records, 0.048% suite-wide).
- **Infinite Values (+Inf)**: Infinite values occur exclusively in `Flow Packets/s` (2,867 records) and `Flow Bytes/s` (1,514 records). In 100.0% of cases, the corresponding `Flow Duration` is exactly $0$.
- **Constant Features**: 8 features are constant zero across all 2.83M records:
  `Bwd PSH Flags`, `Bwd URG Flags`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.
- **Semi-Constant Features**: `Fwd URG Flags` and `CWE Flag Count` are constant 0 in 7 datasets, activating only 315 times in Thursday Afternoon Benign traffic.

---

## 5. Master Label Distribution
| Rank | Class Label | Suite Count | Suite Percentage (%) | Attack Category |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `BENIGN` | 2,273,097 | 80.3004% | Normal Background Activity |
| 2 | `DoS Hulk` | 231,073 | 8.1630% | Volumetric HTTP Request Flood |
| 3 | `PortScan` | 158,930 | 5.6144% | Network Reconnaissance (Nmap top-1000) |
| 4 | `DDoS` | 128,027 | 4.5227% | Distributed LOIC Flood |
| 5 | `DoS GoldenEye` | 10,293 | 0.3636% | Multi-Threaded Keep-Alive Flood |
| 6 | `FTP-Patator` | 7,938 | 0.2804% | Port 21 Authentication Brute Force |
| 7 | `SSH-Patator` | 5,897 | 0.2083% | Port 22 SSH Protocol Brute Force |
| 8 | `DoS slowloris` | 5,796 | 0.2048% | Connection Exhaustion Slow HTTP |
| 9 | `DoS Slowhttptest` | 5,499 | 0.1943% | Incomplete Request Header Starvation |
| 10 | `Bot` | 1,966 | 0.0695% | ARES Botnet C2 Beaconing |
| 11 | `Web Attack - Brute Force` | 1,507 | 0.0532% | Web Fuzzing / Form Brute Force |
| 12 | `Web Attack - XSS` | 652 | 0.0230% | Cross-Site Scripting Parameter Injection |
| 13 | `Infiltration` | 36 | 0.0013% | Exploitation & Post-Compromise Backdoor |
| 14 | `Web Attack - Sql Injection` | 21 | 0.0007% | Interactive SQL Query Injection |
| 15 | `Heartbleed` | 11 | 0.0004% | OpenSSL Memory Leak Exploit |

---

## 6. Feature Analysis & Distributions
- **Flow Duration**: Displays extreme multimodal separation. 5% of flows terminate in $<3\ \mu\text{s}$ (DNS queries and PortScan probes), median is $\sim 31.3\ \text{ms}$, and the 95th percentile reaches $102.2\ \text{seconds}$.
- **Flow Directionality**: Across normal benign traffic, 85.4% of flows are bidirectional, 14.6% are forward-only (unanswered queries), and 0% are backward-only. In contrast, automated attacks (PortScan, Slowhttptest, Web Fuzzing) exhibit $>95\%$ forward-only / 0-backward packet profiles.
- **Skewness Profile**: 22 flow features exhibit severe skewness ($|\text{skew}| > 20$), confirming the necessity of non-linear log transformations prior to distance-based or linear modeling.

---

## 7. Cybersecurity-Specific Findings

### A. Authentication Brute Force (Tuesday: FTP & SSH Patator)
- **FTP-Patator (Port 21)**: Automated dictionary iterations characterized by compact command exchanges. Median backward packet size is **exactly 76 bytes** (matching server response `530 Login incorrect`).
- **SSH-Patator (Port 22)**: Encrypted handshake and key exchange negotiation followed by auth failure produces a distinct **2,009-byte median backward length** across 15–22 packets.

### B. Denial of Service & Heartbleed (Wednesday)
- **Volumetric DoS (Hulk, GoldenEye)**: 100% target Port 80, flooding the web server with high-rate HTTP requests. Hulk produces 949 zero-duration burst flows resulting in infinite packet rates.
- **Slow-and-Low DoS (slowloris, Slowhttptest)**: Designed to exhaust server thread pools without high packet volume. `DoS Slowhttptest` has a **median Backward Packets of exactly 0** (unidirectional request starvation).
- **Heartbleed Exploit (Port 444)**: 11 flows with massive memory leakage (average duration: 110.7 seconds, average backward exfiltration: **7.28 MB of process memory** per flow).

### C. Web Application Attacks (Thursday Morning)
- **Fuzzing vs Interactive Exploitation**:
  - `Web Attack - Brute Force` & `XSS` exhibit 0 median backward packets (rapid fuzzing scripts).
  - `Web Attack - Sql Injection` (21 flows) shows complete bidirectional interactive dialogue (median 4 forward packets, 3 backward packets; median forward payload: 460 bytes, backward: 530 bytes).

### D. Multi-Stage Infiltration (Thursday Afternoon)
- 36 flows targeting **Port 444** (backdoor shell listener). Characterized by long flow durations (median 93.2 seconds), symmetric packet counts (26 forward, 26 backward), and significant forward payload size (296 bytes) vs minimal execution ACK return (7 bytes).

### E. Botnet Command & Control (Friday Morning)
- ARES botnet clients check in with C2 masters primarily over **Port 8080** (64.1%) using periodic polling. `Flow IAT Mean` displays clear periodic beacon clustering (median 23.4 ms vs benign median 2.8 ms).

### F. Port Scanning (Friday Afternoon)
- Probed exactly **1,000 distinct destination ports** (Nmap top-1000 spectrum).
- Over 99.07% of PortScan flows consist of **1-packet probes** (`Total Fwd Packets == 1`), generating 68,111 exact duplicate flow vectors (42.86% within class).

### G. Distributed Denial of Service (Friday Afternoon: LOIC)
- Massive HTTP flood targeting Port 80 from distributed attacker nodes. Distinct from Wednesday Hulk because multi-source randomized client ports maintained a low duplicate rate (1.17%).

---

## 8. Outlier and Infinite-Value Findings
- **Cybersecurity Outlier Principle**: Extreme values in network telemetry often represent the core attack payload (e.g. Heartbleed's 7.28 MB memory dump, DoS Hulk's $10^6$ packets/s rate). Outliers must **not** be clipped or discarded.
- **Infinite Values Root Cause**:
  | Feature | Total Inf Count | Exact Root Cause | Solution |
  | :--- | :--- | :--- | :--- |
  | `Flow Packets/s` | 2,867 | `Flow Duration == 0` (Zero denominator) | Impute nominal duration of $1.0\ \mu\text{s}$ |
  | `Flow Bytes/s` | 1,514 | `Flow Duration == 0` & `Total Bytes > 0` | Impute nominal duration of $1.0\ \mu\text{s}$ |

---

## 9. Correlation & Redundancy Analysis
63 feature pairs share $|r| \ge 0.90$. 8 exact duplicate pairs ($r = 1.0000$) were identified and recommended for pruning:
1. `Bwd Packet Length Mean` $\equiv$ `Avg Bwd Segment Size`
2. `Fwd Packet Length Mean` $\equiv$ `Avg Fwd Segment Size`
3. `Fwd Header Length` $\equiv$ `Fwd Header Length.1` (Column 14 $\equiv$ Column 34)
4. `Fwd PSH Flags` $\equiv$ `SYN Flag Count`
5. `Total Fwd Packets` $\equiv$ `Subflow Fwd Packets`
6. `Total Backward Packets` $\equiv$ `Subflow Bwd Packets`
7. `Total Length of Fwd Packets` $\equiv$ `Subflow Fwd Bytes`
8. `Total Length of Bwd Packets` $\equiv$ `Subflow Bwd Bytes`

---

## 10. Cross-Dataset Distribution Shift & Benign Drift
- **Benign Baseline Stability**: Normal background traffic across Monday, Tuesday, Wednesday, Thursday, and Friday morning demonstrates consistent service distributions (DNS $\sim 40\%$, HTTPS $\sim 22\%$, HTTP $\sim 10\%$).
- **Attack-Induced Congestion Drift**: During heavy flood attacks (Friday DDoS and PortScan), benign HTTPS connection completions dropped to 13.8% due to buffer congestion and dropped SYN-ACK packets.
- **Anomaly Detection Takeaway**: An unsupervised anomaly detector trained on Monday Benign traffic will maintain high fidelity across days when scaled with robust quantiles.

---

## 11. Data Leakage Risks & Mitigations
1. **Duplicate Record Leakage (Critical)**: 255,446 duplicate rows exist. Random splitting creates identical train/test clones (42.8% of PortScan). **Mitigation**: Deduplicate training splits.
2. **Destination Port Memorization (High)**: Attacks targeted fixed ports (21, 22, 80, 444). **Mitigation**: Exclude `Destination Port` from behavioral anomaly detection features.
3. **Temporal Burst Correlation (High)**: Attacks occurred in narrow scheduled windows. **Mitigation**: Use cross-day evaluation (Train Monday, Test Tuesday–Friday).
4. **Global Preprocessing Leakage (Medium)**: **Mitigation**: Use strict Scikit-Learn pipelines fitted strictly on training data.

---

## 12. Isolation Forest Readiness Assessment
- **Feature Space**: 65 to 68 clean active numerical features after dropping 8 constant columns, 1 duplicate column, and `Destination Port`.
- **Scaling Requirements**: Apply $\log_{10}(x + 1)$ to heavy-tailed volumetric metrics followed by `RobustScaler`.
- **Training Strategy**: Train on Monday Benign traffic (529k flows) with `max_samples=256` to `1024` and `n_estimators=100`–`200`.

---

## 13. Preprocessing Recommendations Summary
1. Standardize column names (`df.columns.str.strip()`) and drop duplicate index 34.
2. Sanitize Thursday Web Attack non-ASCII labels.
3. Impute zero-duration flows with $1.0\ \mu\text{s}$ to deterministically eliminate infinite rates.
4. Drop 8 zero-variance constant features and 7 redundant collinear pairs.
5. Deduplicate training sets prior to model training.
6. Apply log transforms and robust quantile scaling.

---

## 14. Dataset Limitations
- **Synthetic Testbed Environment**: IP/Port addressing was static during recording, introducing potential port-memorization artifacts if not controlled.
- **Micro-Minority Classes**: Heartbleed (11 flows) and SQL Injection (21 flows) cannot be reliably evaluated with standard 5-fold cross-validation without aggregation or synthetic oversampling.
- **Flow-Level Granularity**: CICFlowMeter captures statistical metadata rather than full deep packet inspection (DPI) payload strings.

---

## 15. Final EDA Verdict

# 🟢 READY FOR PREPROCESSING

**Justification**:
1. All 8 CSV datasets have been thoroughly explored, validated, and cataloged (2,830,743 records).
2. Data quality anomalies (1,358 NaNs, 2,867 Infs) have been root-caused and assigned deterministic preprocessing solutions.
3. Attack mechanics across all 14 intrusion classes have been verified and interpreted with network domain semantics.
4. Data leakage channels (duplicates, port memorization, temporal bursts) have been audited with concrete mitigations.
5. Isolation Forest and supervised anomaly detection pipelines have clear, actionable, evidence-based blueprints.
