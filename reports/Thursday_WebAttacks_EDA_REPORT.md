# Dataset 4: Thursday-WorkingHours-Morning-WebAttacks EDA Report

## 1. Dataset Overview
- **File**: `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`
- **File Size**: 49.61 MB
- **Total Records**: 170,366
- **Total Columns**: 79 (78 features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~102.7 MB in-memory
- **Intended Attack Scenarios**: Application-layer Web Attacks targeting HTTP services (Web Attack - Brute Force, Web Attack - XSS, and Web Attack - SQL Injection).

---

## 2. Validation Status: WARNING (Encoding Artifact in Labels)
- **Label Encoding Issue**:
  - The raw CSV contains Windows-1252 byte `0x96` (en-dash `–`) in attack label names (e.g. `'Web Attack \x96 Brute Force'`).
  - Standard UTF-8 decoders interpret this as the Unicode replacement character `\ufffd` (`ï¿½`).
  - **Resolution**: Maintain raw strings for integrity while defining normalized strings (`'Web Attack - Brute Force'`, `'Web Attack - XSS'`, `'Web Attack - Sql Injection'`) for modeling.

---

## 3. Data Quality & Anomalies
- **Missing Values (NaN)**: 20 records in `Flow Bytes/s` (0.012%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 135 records
  - `Flow Bytes/s`: 115 records
  - **Root Cause**: 100% (135/135) of Inf records have `Flow Duration == 0` in background benign traffic.
- **Duplicate Records**: 6,066 rows (3.56%).
- **Constant Zero-Variance Features (10)**:
  `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.

---

## 4. Label Distribution & Extreme Imbalance
| Raw Label String | Normalized Label | Count | Percentage | Class Ratio (vs Majority) |
| :--- | :--- | :--- | :--- | :--- |
| `'BENIGN'` | `BENIGN` | 168,186 | 98.7204% | 1.0000 (Majority) |
| `'Web Attack \x96 Brute Force'` | `Web Attack - Brute Force` | 1,507 | 0.8846% | 1 : 111.6 |
| `'Web Attack \x96 XSS'` | `Web Attack - XSS` | 652 | 0.3827% | 1 : 257.9 |
| `'Web Attack \x96 Sql Injection'` | `Web Attack - Sql Injection` | 21 | 0.0123% | 1 : 8,008.9 |

Total Web Attack Traffic: 2,180 flows (1.28%).

---

## 5. Cybersecurity & Network Behavioral Findings
### A. Destination Port Targeting
- **100.0% of all Web Attack instances (2,180 flows)** targeted **Port 80** (HTTP Web Server).
- Background benign traffic on Thursday morning was distributed across Port 53 (DNS, 76,545 flows), Port 443 (HTTPS, 35,833 flows), and Port 80 (HTTP, 18,682 flows).

### B. Attack Mechanics & Behavioral Signatures
1. **Web Attack - Brute Force & XSS (Fuzzing/Scanning Automation)**:
   - Automated injection scripts fired rapid HTTP GET/POST queries with long URL parameters containing attack payloads.
   - For both Brute Force and XSS, the **median Backward Packets is 0** and **median Backward Length is 0 bytes**. The client aborted connections or the server closed sockets before returning application data.
2. **Web Attack - SQL Injection (Interactive Exploit Delivery)**:
   - Only 21 total records exist in the entire dataset.
   - Flows show interactive request-response exchanges (Median: 4 Forward packets, 3 Backward packets).
   - Median request payload: **460 bytes** (containing SQL syntax strings like `UNION SELECT`, `' OR '1'='1`).
   - Median response payload: **530 bytes** (server response code and database error/content returned).

---

## 6. Outlier & Feature Dynamics
- Web attack forward packet lengths are significantly larger than benign Port 80 HTTP requests due to appended parameter payloads, XSS `<script>` tags, and SQL syntax strings.

---

## 7. Key Visualizations
- `figures/thursday_webattacks/thursday_webattacks_label_distribution.png`: Log-scale class distribution.
- `figures/thursday_webattacks/thursday_webattacks_fwd_payload_length.png`: Boxplot of forward payload length showing larger request payloads in web attacks.
- `figures/thursday_webattacks/thursday_webattacks_request_response_scatter.png`: Scatter plot of Request vs Response payload lengths.

---

## 8. Preprocessing & ML Readiness Implications
1. **Label Sanitization**: Parser must explicitly map non-ASCII byte strings (`\x96`) to standard ASCII strings before model training.
2. **Extreme Class Imbalance (SQL Injection)**: 21 instances require synthetic oversampling (SMOTE) or grouping all three subclasses into a single `'Web Attack'` meta-class during supervised modeling.
3. **Payload Inspection Limitations**: Because CICFlowMeter captures statistical flow features rather than raw application-layer packet contents (DPI), web attack detection relies on request size, forward-to-backward ratios, and flow timing.

---

## 9. ML & Isolation Forest Readiness: 🟢 READY
Web attacks show distinct asymmetry and request length variations suitable for anomaly detection.
