# CICIDS2017 Schema Compatibility Report

## 1. Schema Overview

- **Total CSV Datasets**: 8
- **Reported Column Count per Dataset**: 79 columns in all 8 CSV files.
- **Unique Stripped Column Count**: 78 distinct feature names (due to 1 duplicate column name `Fwd Header Length`).

## 2. Duplicate Column Discovery: `Fwd Header Length`

> [!WARNING]
> Every CSV contains two columns named `Fwd Header Length` (or ` Fwd Header Length.1` in some parsers):
> - Column index 14: ` Fwd Header Length` (Forward Header Length in bytes)
> - Column index 34: ` Fwd Header Length` (or ` Fwd Header Length.1`)
> In actual flow data, both columns contain **identical values** across all records. This is a known CICFlowMeter export redundancy.

## 3. Whitespace & Casing Inconsistencies

A large majority of column headers contain leading whitespaces in the raw CSV (e.g. `' Flow Duration'`, `' Destination Port'`, `' Label'`).
When loading with standard parsers, these leading spaces must be explicitly handled (e.g. `df.columns = df.columns.str.strip()`) to ensure consistent indexing across days.

## 4. Column Alignment Across All 8 Datasets

| Index | Raw Column Name (Monday) | Stripped Name | Data Type Category |
| :--- | :--- | :--- | :--- |
| 0 | `'Destination Port'` | `Destination Port` | Identifier/Port |
| 1 | `' Flow Duration'` | `Flow Duration` | Numerical Flow Metric |
| 2 | `' Total Fwd Packets'` | `Total Fwd Packets` | Numerical Flow Metric |
| 3 | `' Total Backward Packets'` | `Total Backward Packets` | Numerical Flow Metric |
| 4 | `'Total Length of Fwd Packets'` | `Total Length of Fwd Packets` | Numerical Flow Metric |
| 5 | `' Total Length of Bwd Packets'` | `Total Length of Bwd Packets` | Numerical Flow Metric |
| 6 | `' Fwd Packet Length Max'` | `Fwd Packet Length Max` | Numerical Flow Metric |
| 7 | `' Fwd Packet Length Min'` | `Fwd Packet Length Min` | Numerical Flow Metric |
| 8 | `' Fwd Packet Length Mean'` | `Fwd Packet Length Mean` | Numerical Flow Metric |
| 9 | `' Fwd Packet Length Std'` | `Fwd Packet Length Std` | Numerical Flow Metric |
| 10 | `'Bwd Packet Length Max'` | `Bwd Packet Length Max` | Numerical Flow Metric |
| 11 | `' Bwd Packet Length Min'` | `Bwd Packet Length Min` | Numerical Flow Metric |
| 12 | `' Bwd Packet Length Mean'` | `Bwd Packet Length Mean` | Numerical Flow Metric |
| 13 | `' Bwd Packet Length Std'` | `Bwd Packet Length Std` | Numerical Flow Metric |
| 14 | `'Flow Bytes/s'` | `Flow Bytes/s` | Numerical Flow Metric |
| 15 | `' Flow Packets/s'` | `Flow Packets/s` | Numerical Flow Metric |
| 16 | `' Flow IAT Mean'` | `Flow IAT Mean` | Numerical Flow Metric |
| 17 | `' Flow IAT Std'` | `Flow IAT Std` | Numerical Flow Metric |
| 18 | `' Flow IAT Max'` | `Flow IAT Max` | Numerical Flow Metric |
| 19 | `' Flow IAT Min'` | `Flow IAT Min` | Numerical Flow Metric |
| 20 | `'Fwd IAT Total'` | `Fwd IAT Total` | Numerical Flow Metric |
| 21 | `' Fwd IAT Mean'` | `Fwd IAT Mean` | Numerical Flow Metric |
| 22 | `' Fwd IAT Std'` | `Fwd IAT Std` | Numerical Flow Metric |
| 23 | `' Fwd IAT Max'` | `Fwd IAT Max` | Numerical Flow Metric |
| 24 | `' Fwd IAT Min'` | `Fwd IAT Min` | Numerical Flow Metric |
| 25 | `'Bwd IAT Total'` | `Bwd IAT Total` | Numerical Flow Metric |
| 26 | `' Bwd IAT Mean'` | `Bwd IAT Mean` | Numerical Flow Metric |
| 27 | `' Bwd IAT Std'` | `Bwd IAT Std` | Numerical Flow Metric |
| 28 | `' Bwd IAT Max'` | `Bwd IAT Max` | Numerical Flow Metric |
| 29 | `' Bwd IAT Min'` | `Bwd IAT Min` | Numerical Flow Metric |
| 30 | `'Fwd PSH Flags'` | `Fwd PSH Flags` | Numerical Flow Metric |
| 31 | `' Bwd PSH Flags'` | `Bwd PSH Flags` | Numerical Flow Metric |
| 32 | `' Fwd URG Flags'` | `Fwd URG Flags` | Numerical Flow Metric |
| 33 | `' Bwd URG Flags'` | `Bwd URG Flags` | Numerical Flow Metric |
| 34 | `' Fwd Header Length'` | `Fwd Header Length` **(DUPLICATE)** | Numerical Flow Metric |
| 35 | `' Bwd Header Length'` | `Bwd Header Length` | Numerical Flow Metric |
| 36 | `'Fwd Packets/s'` | `Fwd Packets/s` | Numerical Flow Metric |
| 37 | `' Bwd Packets/s'` | `Bwd Packets/s` | Numerical Flow Metric |
| 38 | `' Min Packet Length'` | `Min Packet Length` | Numerical Flow Metric |
| 39 | `' Max Packet Length'` | `Max Packet Length` | Numerical Flow Metric |
| 40 | `' Packet Length Mean'` | `Packet Length Mean` | Numerical Flow Metric |
| 41 | `' Packet Length Std'` | `Packet Length Std` | Numerical Flow Metric |
| 42 | `' Packet Length Variance'` | `Packet Length Variance` | Numerical Flow Metric |
| 43 | `'FIN Flag Count'` | `FIN Flag Count` | Numerical Flow Metric |
| 44 | `' SYN Flag Count'` | `SYN Flag Count` | Numerical Flow Metric |
| 45 | `' RST Flag Count'` | `RST Flag Count` | Numerical Flow Metric |
| 46 | `' PSH Flag Count'` | `PSH Flag Count` | Numerical Flow Metric |
| 47 | `' ACK Flag Count'` | `ACK Flag Count` | Numerical Flow Metric |
| 48 | `' URG Flag Count'` | `URG Flag Count` | Numerical Flow Metric |
| 49 | `' CWE Flag Count'` | `CWE Flag Count` | Numerical Flow Metric |
| 50 | `' ECE Flag Count'` | `ECE Flag Count` | Numerical Flow Metric |
| 51 | `' Down/Up Ratio'` | `Down/Up Ratio` | Numerical Flow Metric |
| 52 | `' Average Packet Size'` | `Average Packet Size` | Numerical Flow Metric |
| 53 | `' Avg Fwd Segment Size'` | `Avg Fwd Segment Size` | Numerical Flow Metric |
| 54 | `' Avg Bwd Segment Size'` | `Avg Bwd Segment Size` | Numerical Flow Metric |
| 55 | `' Fwd Header Length'` | `Fwd Header Length` | Numerical Flow Metric |
| 56 | `'Fwd Avg Bytes/Bulk'` | `Fwd Avg Bytes/Bulk` | Numerical Flow Metric |
| 57 | `' Fwd Avg Packets/Bulk'` | `Fwd Avg Packets/Bulk` | Numerical Flow Metric |
| 58 | `' Fwd Avg Bulk Rate'` | `Fwd Avg Bulk Rate` | Numerical Flow Metric |
| 59 | `' Bwd Avg Bytes/Bulk'` | `Bwd Avg Bytes/Bulk` | Numerical Flow Metric |
| 60 | `' Bwd Avg Packets/Bulk'` | `Bwd Avg Packets/Bulk` | Numerical Flow Metric |
| 61 | `'Bwd Avg Bulk Rate'` | `Bwd Avg Bulk Rate` | Numerical Flow Metric |
| 62 | `'Subflow Fwd Packets'` | `Subflow Fwd Packets` | Numerical Flow Metric |
| 63 | `' Subflow Fwd Bytes'` | `Subflow Fwd Bytes` | Numerical Flow Metric |
| 64 | `' Subflow Bwd Packets'` | `Subflow Bwd Packets` | Numerical Flow Metric |
| 65 | `' Subflow Bwd Bytes'` | `Subflow Bwd Bytes` | Numerical Flow Metric |
| 66 | `'Init_Win_bytes_forward'` | `Init_Win_bytes_forward` | Numerical Flow Metric |
| 67 | `' Init_Win_bytes_backward'` | `Init_Win_bytes_backward` | Numerical Flow Metric |
| 68 | `' act_data_pkt_fwd'` | `act_data_pkt_fwd` | Numerical Flow Metric |
| 69 | `' min_seg_size_forward'` | `min_seg_size_forward` | Numerical Flow Metric |
| 70 | `'Active Mean'` | `Active Mean` | Numerical Flow Metric |
| 71 | `' Active Std'` | `Active Std` | Numerical Flow Metric |
| 72 | `' Active Max'` | `Active Max` | Numerical Flow Metric |
| 73 | `' Active Min'` | `Active Min` | Numerical Flow Metric |
| 74 | `'Idle Mean'` | `Idle Mean` | Numerical Flow Metric |
| 75 | `' Idle Std'` | `Idle Std` | Numerical Flow Metric |
| 76 | `' Idle Max'` | `Idle Max` | Numerical Flow Metric |
| 77 | `' Idle Min'` | `Idle Min` | Numerical Flow Metric |
| 78 | `' Label'` | `Label` | Label (Categorical/String) |
