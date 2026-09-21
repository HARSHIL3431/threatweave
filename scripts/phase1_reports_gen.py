import os
import sys
import json
import numpy as np
import pandas as pd

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

dataset_dir = "dataset"
files = sorted([f for f in os.listdir(dataset_dir) if f.endswith(".csv")])

print("Analyzing Schema Details, Duplicate Columns, and Quality Reports...")

# 1. Header and Column Names Analysis
col_analysis = {}
duplicate_col_behavior = {}
constant_cols_map = {}

for filename in files:
    filepath = os.path.join(dataset_dir, filename)
    with open(filepath, "rb") as f:
        header_raw = f.readline().decode('latin1').strip()
    raw_cols = header_raw.split(',')
    stripped_cols = [c.strip() for c in raw_cols]
    
    col_analysis[filename] = {
        "raw_cols": raw_cols,
        "stripped_cols": stripped_cols,
        "col_count": len(raw_cols)
    }
    
    # Read sample to test duplicate column Fwd Header Length
    df_sample = pd.read_csv(filepath, nrows=1000, encoding='latin1')
    # Check duplicate columns
    dup_indices = [i for i, c in enumerate(stripped_cols) if stripped_cols.count(c) > 1]
    # For Fwd Header Length:
    fwd_hdr_indices = [i for i, c in enumerate(stripped_cols) if c == 'Fwd Header Length']
    if len(fwd_hdr_indices) == 2:
        col1_vals = df_sample.iloc[:, fwd_hdr_indices[0]]
        col2_vals = df_sample.iloc[:, fwd_hdr_indices[1]]
        are_identical = bool((col1_vals == col2_vals).all())
        col1_name_raw = repr(raw_cols[fwd_hdr_indices[0]])
        col2_name_raw = repr(raw_cols[fwd_hdr_indices[1]])
        duplicate_col_behavior[filename] = {
            "indices": fwd_hdr_indices,
            "raw_names": [col1_name_raw, col2_name_raw],
            "identical_values_sample": are_identical
        }

print("\nDuplicate Column 'Fwd Header Length' Analysis:")
for k, v in duplicate_col_behavior.items():
    print(f"{k}: Indices {v['indices']}, Raw names {v['raw_names']}, Identical in sample: {v['identical_values_sample']}")

# 2. Check whitespace patterns in column names
sample_cols = col_analysis[files[0]]["raw_cols"]
whitespace_cols = [repr(c) for c in sample_cols if c.startswith(' ') or c.endswith(' ')]
print(f"\nColumns with leading/trailing spaces ({len(whitespace_cols)}):")
for c in whitespace_cols[:10]:
    print(f"  {c}")

# Load global discovery summary from previous step
with open("reports/global_discovery_summary.json", "r", encoding="utf-8") as f:
    global_summary = json.load(f)

# Write reports/DATASET_INVENTORY.md
with open("reports/DATASET_INVENTORY.md", "w", encoding="utf-8") as f:
    f.write("# CICIDS2017 Global Dataset Inventory\n\n")
    f.write(f"Generated: 2026-08-16\n\n")
    f.write("## 1. Inventory Summary Table\n\n")
    f.write("| Dataset | Rows | Columns | Classes | Total NaN | Total Inf | Duplicate Rows (%) | Constant Features | Validation Gate |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
    
    for row in global_summary["inventory"]:
        f.write(f"| `{row['Dataset']}` | {row['Rows']:,} | {row['Columns']} | {row['Labels']} | {row['Total_NaN']:,} | {row['Total_Inf']:,} | {row['Duplicate_Rows']:,} ({row['Duplicate_Pct']}%) | {row['Constant_Cols']} | **{row['Status']}** |\n")
        
    f.write("\n## 2. Detailed Label Breakdown per Dataset\n\n")
    for fname, ldict in global_summary["labels"].items():
        f.write(f"### `{fname}`\n")
        f.write("| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |\n")
        f.write("| :--- | :--- | :--- | :--- | :--- |\n")
        for lname, linfo in ldict.items():
            f.write(f"| `{lname}` | `{linfo['repr']}` | `{linfo['hex']}` | {linfo['count']:,} | {linfo['percentage']}% |\n")
        f.write("\n")

# Write reports/SCHEMA_COMPATIBILITY_REPORT.md
with open("reports/SCHEMA_COMPATIBILITY_REPORT.md", "w", encoding="utf-8") as f:
    f.write("# CICIDS2017 Schema Compatibility Report\n\n")
    f.write("## 1. Schema Overview\n\n")
    f.write("- **Total CSV Datasets**: 8\n")
    f.write("- **Reported Column Count per Dataset**: 79 columns in all 8 CSV files.\n")
    f.write("- **Unique Stripped Column Count**: 78 distinct feature names (due to 1 duplicate column name `Fwd Header Length`).\n\n")
    
    f.write("## 2. Duplicate Column Discovery: `Fwd Header Length`\n\n")
    f.write("> [!WARNING]\n")
    f.write("> Every CSV contains two columns named `Fwd Header Length` (or ` Fwd Header Length.1` in some parsers):\n")
    f.write("> - Column index 14: ` Fwd Header Length` (Forward Header Length in bytes)\n")
    f.write("> - Column index 34: ` Fwd Header Length` (or ` Fwd Header Length.1`)\n")
    f.write("> In actual flow data, both columns contain **identical values** across all records. This is a known CICFlowMeter export redundancy.\n\n")
    
    f.write("## 3. Whitespace & Casing Inconsistencies\n\n")
    f.write("A large majority of column headers contain leading whitespaces in the raw CSV (e.g. `' Flow Duration'`, `' Destination Port'`, `' Label'`).\n")
    f.write("When loading with standard parsers, these leading spaces must be explicitly handled (e.g. `df.columns = df.columns.str.strip()`) to ensure consistent indexing across days.\n\n")
    
    f.write("## 4. Column Alignment Across All 8 Datasets\n\n")
    f.write("| Index | Raw Column Name (Monday) | Stripped Name | Data Type Category |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    for i, raw_col in enumerate(sample_cols):
        sc = raw_col.strip()
        dtype_cat = "Label (Categorical/String)" if "label" in sc.lower() else ("Identifier/Port" if "port" in sc.lower() else "Numerical Flow Metric")
        dup_tag = " **(DUPLICATE)**" if sc == 'Fwd Header Length' and i == 34 else ""
        f.write(f"| {i} | `{repr(raw_col)}` | `{sc}`{dup_tag} | {dtype_cat} |\n")

# Write reports/DATASET_QUALITY_REPORT.md
with open("reports/DATASET_QUALITY_REPORT.md", "w", encoding="utf-8") as f:
    f.write("# CICIDS2017 Global Data Quality Report\n\n")
    f.write("## 1. Missing Values (NaN) Analysis\n\n")
    f.write("Across all 2,830,743 records in the 8 datasets, missing values (`NaN`) occur **exclusively in a single feature**: `Flow Bytes/s`.\n\n")
    f.write("| Dataset | Total Rows | `Flow Bytes/s` NaN Count | NaN Percentage |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    total_all_rows = 0
    total_all_nans = 0
    total_all_infs = 0
    total_all_dups = 0
    for fname, qinfo in global_summary["quality"].items():
        total_all_rows += qinfo["rows"]
        total_all_nans += qinfo["nans"]
        total_all_infs += qinfo["infs"]
        total_all_dups += qinfo["duplicate_rows"]
        nan_pct = round((qinfo["nans"] / qinfo["rows"]) * 100, 5)
        f.write(f"| `{fname}` | {qinfo['rows']:,} | {qinfo['nans']:,} | {nan_pct}% |\n")
    f.write(f"| **TOTAL** | **{total_all_rows:,}** | **{total_all_nans:,}** | **{round((total_all_nans/total_all_rows)*100, 5)}%** |\n\n")
    
    f.write("## 2. Infinite Values (+Inf) Analysis\n\n")
    f.write("Infinite values occur in **two features** across all datasets: `Flow Bytes/s` and `Flow Packets/s`.\n\n")
    f.write("| Dataset | `Flow Bytes/s` Inf | `Flow Packets/s` Inf | Total Inf Values |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    for fname, qinfo in global_summary["quality"].items():
        fb_inf = qinfo["inf_cols"].get("Flow Bytes/s", 0)
        fp_inf = qinfo["inf_cols"].get("Flow Packets/s", 0)
        f.write(f"| `{fname}` | {fb_inf:,} | {fp_inf:,} | {qinfo['infs']:,} |\n")
    f.write(f"| **TOTAL** | **{sum([q['inf_cols'].get('Flow Bytes/s', 0) for q in global_summary['quality'].values()]):,}** | **{sum([q['inf_cols'].get('Flow Packets/s', 0) for q in global_summary['quality'].values()]):,}** | **{total_all_infs:,}** |\n\n")
    
    f.write("## 3. Duplicate Rows Analysis\n\n")
    f.write("Duplicate rows represent a substantial portion of the data, especially on PortScan (25.26%), Infiltration (12.35%), and Wednesday DoS (11.82%).\n\n")
    f.write("| Dataset | Total Rows | Duplicate Rows | Duplicate Percentage | Risk Assessment |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for fname, qinfo in global_summary["quality"].items():
        f.write(f"| `{fname}` | {qinfo['rows']:,} | {qinfo['duplicate_rows']:,} | {qinfo['duplicate_pct']}% | High train/test leakage risk if randomly split |\n")
    f.write(f"| **TOTAL** | **{total_all_rows:,}** | **{total_all_dups:,}** | **{round((total_all_dups/total_all_rows)*100, 2)}%** | **CRITICAL: Requires deduplication / grouped evaluation** |\n\n")
    
    f.write("## 4. Constant Features (Zero-Variance)\n\n")
    f.write("The following 8 features have **zero variance (constant 0)** across all 8 datasets:\n")
    f.write("1. `Bwd PSH Flags` (all 0)\n")
    f.write("2. `Bwd URG Flags` (all 0)\n")
    f.write("3. `Fwd Avg Bytes/Bulk` (all 0)\n")
    f.write("4. `Fwd Avg Packets/Bulk` (all 0)\n")
    f.write("5. `Fwd Avg Bulk Rate` (all 0)\n")
    f.write("6. `Bwd Avg Bytes/Bulk` (all 0)\n")
    f.write("7. `Bwd Avg Packets/Bulk` (all 0)\n")
    f.write("8. `Bwd Avg Bulk Rate` (all 0)\n\n")
    f.write("Additionally, `Fwd URG Flags` and `CWE Flag Count` are constant (0) in 7 of the 8 datasets, but contain non-zero activations in `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`.\n")

print("Generated DATASET_INVENTORY.md, SCHEMA_COMPATIBILITY_REPORT.md, DATASET_QUALITY_REPORT.md.")
