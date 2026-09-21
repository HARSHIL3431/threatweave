# Dataset 6: Friday-WorkingHours-Morning EDA Report

## 1. Dataset Overview
- **File**: `Friday-WorkingHours-Morning.pcap_ISCX.csv`
- **File Size**: 55.62 MB
- **Total Records**: 191,033
- **Total Columns**: 79 (78 distinct features + 1 duplicate column `Fwd Header Length`)
- **Memory Footprint**: ~115.1 MB in-memory
- **Intended Attack Scenario**: Botnet infection and Command-and-Control (C2) communication (ARES Botnet framework).

---

## 2. Validation Status: PASS
- **Row Count Verification**: 191,033 rows loaded cleanly.
- **Attack Class Presence**: 1,966 confirmed `Bot` flows present.
- **Label Integrity**: 100% valid string labels.

---

## 3. Data Quality & Anomalies
- **Missing Values (NaN)**: 28 records in `Flow Bytes/s` (0.015%).
- **Infinite Values (+Inf)**:
  - `Flow Packets/s`: 122 records (112 BENIGN, 10 Bot)
  - `Flow Bytes/s`: 94 records
  - **Root Cause**: 100% (122/122) of Inf records have `Flow Duration == 0`.
- **Duplicate Records**: 6,888 rows (3.61%).
- **Constant Zero-Variance Features (10)**:
  `Bwd PSH Flags`, `Fwd URG Flags`, `Bwd URG Flags`, `CWE Flag Count`, `Fwd Avg Bytes/Bulk`, `Fwd Avg Packets/Bulk`, `Fwd Avg Bulk Rate`, `Bwd Avg Bytes/Bulk`, `Bwd Avg Packets/Bulk`, `Bwd Avg Bulk Rate`.

---

## 4. Label Distribution & Class Imbalance
| Class Label | Count | Percentage | Class Ratio (vs Majority) |
| :--- | :--- | :--- | :--- |
| `BENIGN` | 189,067 | 98.9709% | 1.0000 (Majority) |
| `Bot` | 1,966 | 1.0291% | 1 : 96.2 |

Total Botnet Traffic: 1,966 flows (1.03%).

---

## 5. Cybersecurity & Network Behavioral Findings
### A. Destination Port Targeting
- **Port 8080 (HTTP Alternate / C2 Web Master)**: 64.1% of Bot traffic (1,261 flows) communicated directly with an external HTTP C2 server on port 8080.
- Additional dynamic ports (e.g. 53099, 1846, 1847, 3051) were utilized for secondary P2P node coordination and local infection spreading.
- In contrast, background benign traffic targeted Port 53 (DNS, 75,706 flows), Port 443 (HTTPS, 48,011 flows), and Port 80 (HTTP, 19,865 flows).

### B. Command & Control (C2) Traffic Mechanics
- **Periodic Beaconing Signatures**:
  - The ARES bot clients communicate with the C2 master at regular intervals to receive execution instructions.
  - Bot flows display distinctly elevated and clustered **Flow Inter-Arrival Times (Flow IAT Mean)** compared to interactive user-generated web traffic.
- **Payload Exchange Dynamics**:
  - Standard bot polling flows consist of compact HTTP GET/POST queries (Median: 4 Forward packets, 3 Backward packets).
  - Both forward and backward payload sizes remain consistently small during polling phases, spiking only when a command/payload download is dispatched.

---

## 6. Key Visualizations
- `figures/friday_morning/friday_morning_label_distribution.png`: Class distribution showing the 1.03% Bot population.
- `figures/friday_morning/friday_morning_bot_ports.png`: Top destination ports targeted by botnet C2.
- `figures/friday_morning/friday_morning_flow_iat_mean.png`: Boxplot comparing Flow IAT Mean showing periodic beaconing behavior.
- `figures/friday_morning/friday_morning_packet_symmetry.png`: Scatter plot of Forward vs Backward packet counts.

---

## 7. Preprocessing & ML Readiness Implications
1. **Timing Features Importance**: Flow Inter-Arrival Times (`Flow IAT Mean`, `Flow IAT Std`, `Flow IAT Max`) are the primary discriminative features separating automated periodic bot check-ins from sporadic human web requests.
2. **Port 8080 Context**: While port 8080 was the primary C2 channel in this testbed, real-world botnets often tunnel C2 over standard HTTPS (443) or DNS (53). Classifiers should prioritize timing and payload dynamics over destination port to avoid environment-specific memorization.

---

## 8. ML & Isolation Forest Readiness: 🟢 READY
Botnet traffic presents realistic timing and payload size anomalies well-suited for unsupervised anomaly detection.
