# CICIDS2017 Global Data Quality Report

## 1. Missing Values (NaN) Analysis

Across all 2,830,743 records in the 8 datasets, missing values (`NaN`) occur **exclusively in a single feature**: `Flow Bytes/s`.

| Dataset | Total Rows | `Flow Bytes/s` NaN Count | NaN Percentage |
| :--- | :--- | :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 225,745 | 4 | 0.00177% |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 286,467 | 15 | 0.00524% |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 191,033 | 28 | 0.01466% |
| `Monday-WorkingHours.pcap_ISCX.csv` | 529,918 | 64 | 0.01208% |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 288,602 | 18 | 0.00624% |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 170,366 | 20 | 0.01174% |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 445,909 | 201 | 0.04508% |
| `Wednesday-workingHours.pcap_ISCX.csv` | 692,703 | 1,008 | 0.14552% |
| **TOTAL** | **2,830,743** | **1,358** | **0.04797%** |

## 2. Infinite Values (+Inf) Analysis

Infinite values occur in **two features** across all datasets: `Flow Bytes/s` and `Flow Packets/s`.

| Dataset | `Flow Bytes/s` Inf | `Flow Packets/s` Inf | Total Inf Values |
| :--- | :--- | :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 30 | 34 | 64 |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 356 | 371 | 727 |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 94 | 122 | 216 |
| `Monday-WorkingHours.pcap_ISCX.csv` | 373 | 437 | 810 |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 189 | 207 | 396 |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 115 | 135 | 250 |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 63 | 264 | 327 |
| `Wednesday-workingHours.pcap_ISCX.csv` | 289 | 1,297 | 1,586 |
| **TOTAL** | **1,509** | **2,867** | **4,376** |

## 3. Duplicate Rows Analysis

Duplicate rows represent a substantial portion of the data, especially on PortScan (25.26%), Infiltration (12.35%), and Wednesday DoS (11.82%).

| Dataset | Total Rows | Duplicate Rows | Duplicate Percentage | Risk Assessment |
| :--- | :--- | :--- | :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 225,745 | 2,633 | 1.17% | High train/test leakage risk if randomly split |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 286,467 | 72,353 | 25.26% | High train/test leakage risk if randomly split |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 191,033 | 6,888 | 3.61% | High train/test leakage risk if randomly split |
| `Monday-WorkingHours.pcap_ISCX.csv` | 529,918 | 26,935 | 5.08% | High train/test leakage risk if randomly split |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 288,602 | 35,630 | 12.35% | High train/test leakage risk if randomly split |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 170,366 | 6,066 | 3.56% | High train/test leakage risk if randomly split |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 445,909 | 24,065 | 5.4% | High train/test leakage risk if randomly split |
| `Wednesday-workingHours.pcap_ISCX.csv` | 692,703 | 81,909 | 11.82% | High train/test leakage risk if randomly split |
| **TOTAL** | **2,830,743** | **256,479** | **9.06%** | **CRITICAL: Requires deduplication / grouped evaluation** |

## 4. Constant Features (Zero-Variance)

The following 8 features have **zero variance (constant 0)** across all 8 datasets:
1. `Bwd PSH Flags` (all 0)
2. `Bwd URG Flags` (all 0)
3. `Fwd Avg Bytes/Bulk` (all 0)
4. `Fwd Avg Packets/Bulk` (all 0)
5. `Fwd Avg Bulk Rate` (all 0)
6. `Bwd Avg Bytes/Bulk` (all 0)
7. `Bwd Avg Packets/Bulk` (all 0)
8. `Bwd Avg Bulk Rate` (all 0)

Additionally, `Fwd URG Flags` and `CWE Flag Count` are constant (0) in 7 of the 8 datasets, but contain non-zero activations in `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`.
