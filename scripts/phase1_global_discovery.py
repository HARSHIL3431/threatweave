import os
import sys
import glob
import json
import numpy as np
import pandas as pd

# Set stdout to UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

dataset_dir = "dataset"
files = sorted([f for f in os.listdir(dataset_dir) if f.endswith(".csv")])

print(f"Starting Phase 1 Global Discovery across {len(files)} datasets...")

global_results = []
column_sets = {}
label_profiles = {}
quality_profiles = {}
raw_column_lists = {}

for filename in files:
    filepath = os.path.join(dataset_dir, filename)
    print(f"\n=======================================================")
    print(f"Analyzing: {filename}")
    print(f"=======================================================")
    
    # Read raw header bytes to understand exact column names
    with open(filepath, "rb") as f:
        header_raw_bytes = f.readline()
        # Decode using latin1 to preserve exact 1-to-1 byte mappings
        header_text = header_raw_bytes.decode('latin1')
    
    raw_exact_cols = header_text.strip().split(',')
    raw_header_cols = [c.strip() for c in raw_exact_cols]
    raw_column_lists[filename] = raw_exact_cols
    
    # Check for duplicate column names in header
    col_counts = {}
    dup_cols = []
    for c in raw_header_cols:
        col_counts[c] = col_counts.get(c, 0) + 1
        if col_counts[c] == 2:
            dup_cols.append(c)
            
    print(f"Raw column count: {len(raw_exact_cols)}")
    print(f"Stripped column count: {len(raw_header_cols)}")
    if dup_cols:
        print(f"WARNING: Duplicate column names detected in header: {dup_cols}")
    
    # Load dataset with latin1 to safely handle non-ASCII bytes without crashing
    df = pd.read_csv(filepath, encoding='latin1', low_memory=False)
        
    num_rows, num_cols = df.shape
    print(f"Loaded DataFrame: {num_rows:,} rows, {num_cols} columns")
    
    # Identify Label column
    label_col_candidates = [c for c in df.columns if 'label' in c.lower()]
    if not label_col_candidates:
        print("ERROR: No Label column found!")
        label_col = None
    else:
        label_col = label_col_candidates[0]
        print(f"Found Label column: '{label_col}' (raw representation: {repr(label_col)})")
        
    # Analyze Labels
    if label_col:
        raw_labels = df[label_col].value_counts(dropna=False)
        label_dict = {}
        for k, v in raw_labels.items():
            label_str = str(k)
            # Inspect raw bytes
            label_bytes = label_str.encode('latin1', errors='replace').hex()
            label_dict[label_str] = {
                "count": int(v),
                "percentage": round(float(v) / num_rows * 100, 4),
                "repr": repr(label_str),
                "hex": label_bytes
            }
        label_profiles[filename] = label_dict
        print("Label Distribution:")
        for k, v in label_dict.items():
            print(f"  - {v['repr']} (Hex: {v['hex']}): {v['count']:,} ({v['percentage']}%)")
            
    # Check for NaN / Infs across all columns
    nan_counts = df.isna().sum()
    total_nans = int(nan_counts.sum())
    cols_with_nans = nan_counts[nan_counts > 0].to_dict()
    # Strip whitespace from keys for clarity
    cols_with_nans = {k.strip(): int(v) for k, v in cols_with_nans.items()}
    
    # Check for Inf across columns
    inf_counts = {}
    total_infs = 0
    
    for col in df.columns:
        # Convert to numeric if possible for Inf detection
        series_num = pd.to_numeric(df[col], errors='coerce')
        cnt = int(np.isinf(series_num).sum())
        if cnt > 0:
            inf_counts[col.strip()] = cnt
            total_infs += cnt
            
    # Check for duplicate rows
    dup_rows_count = int(df.duplicated().sum())
    dup_rows_pct = round((dup_rows_count / num_rows) * 100, 2) if num_rows > 0 else 0
    
    # Constant columns & near zero variance
    constant_cols = []
    near_zero_var_cols = []
    for col in df.columns:
        num_unique = df[col].nunique(dropna=False)
        if num_unique <= 1:
            constant_cols.append(col.strip())
        else:
            series_num = pd.to_numeric(df[col], errors='coerce')
            if not series_num.isna().all():
                var_val = float(series_num.var(skipna=True))
                if var_val < 1e-5:
                    near_zero_var_cols.append(col.strip())
                
    print(f"Quality Summary: NaNs={total_nans:,}, Infs={total_infs:,}, Duplicate Rows={dup_rows_count:,} ({dup_rows_pct}%), Constant Cols={len(constant_cols)}")
    if cols_with_nans:
        print(f"Columns with NaNs: {cols_with_nans}")
    if inf_counts:
        print(f"Columns with Infs: {inf_counts}")
    if constant_cols:
        print(f"Constant Columns ({len(constant_cols)}): {constant_cols}")
        
    # Validation Gate Decision
    status = "PASS"
    validation_notes = []
    
    if num_rows < 1000:
        status = "BLOCKED"
        validation_notes.append("Unexpectedly small dataset")
    if label_col is None:
        status = "BLOCKED"
        validation_notes.append("Missing Label column")
    if dup_cols:
        validation_notes.append(f"Header contains duplicate column name: {dup_cols}")
    if total_nans > 0:
        validation_notes.append(f"Contains {total_nans} NaN values across {len(cols_with_nans)} columns")
    if total_infs > 0:
        validation_notes.append(f"Contains {total_infs} Inf values across {len(inf_counts)} columns")
    if dup_rows_count > 0:
        validation_notes.append(f"High duplicate row count: {dup_rows_count:,} ({dup_rows_pct}%)")
    if "WebAttacks" in filename:
        for l in label_dict.keys():
            if '\x96' in l or '' in l:
                validation_notes.append(f"Encoding artifact in label string: {repr(l)}")
                
    if status == "PASS" and len(validation_notes) > 0:
        status = "WARNING"
        
    quality_profiles[filename] = {
        "rows": num_rows,
        "cols": num_cols,
        "nans": total_nans,
        "nan_cols": cols_with_nans,
        "infs": total_infs,
        "inf_cols": inf_counts,
        "duplicate_rows": dup_rows_count,
        "duplicate_pct": dup_rows_pct,
        "constant_cols": constant_cols,
        "near_zero_var_cols": near_zero_var_cols,
        "duplicate_header_cols": dup_cols,
        "status": status,
        "notes": "; ".join(validation_notes) if validation_notes else "Clean"
    }
    
    global_results.append({
        "Dataset": filename,
        "Rows": num_rows,
        "Columns": num_cols,
        "Labels": len(label_dict) if label_col else 0,
        "Total_NaN": total_nans,
        "Total_Inf": total_infs,
        "Duplicate_Rows": dup_rows_count,
        "Duplicate_Pct": dup_rows_pct,
        "Constant_Cols": len(constant_cols),
        "Status": status,
        "Validation_Notes": "; ".join(validation_notes) if validation_notes else "Clean"
    })
    
    column_sets[filename] = [c.strip() for c in df.columns]

# Save inventory to CSV
inventory_df = pd.DataFrame(global_results)
inventory_df.to_csv("reports/DATASET_INVENTORY.csv", index=False)

# Dump JSON summary for further reporting
with open("reports/global_discovery_summary.json", "w", encoding="utf-8") as f:
    json.dump({
        "inventory": global_results,
        "quality": quality_profiles,
        "labels": label_profiles,
        "raw_headers": raw_column_lists
    }, f, indent=2)

print("\nPhase 1 Global Discovery completed successfully.")
