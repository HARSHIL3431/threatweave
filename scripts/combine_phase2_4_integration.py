"""
Phase 2-4: Controlled Dataset Integration
===========================================
Schema Harmonization -> Controlled Concatenation -> Validation

This script:
1. Loads each of the 8 source CSVs individually
2. Applies schema harmonization (strip whitespace, drop duplicate column, normalize labels)
3. Adds provenance columns (source_file, source_day, source_row_index)
4. Concatenates into a single controlled DataFrame
5. Validates row counts, label distributions, and provenance integrity
6. Saves the combined raw dataset with a manifest
"""
import os
import sys
import json
import hashlib
import datetime
import warnings
import re

# Force UTF-8 stdout on Windows to handle non-ASCII label characters
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)

# ============================================================
# CONFIGURATION
# ============================================================
DATASET_DIR = "dataset"
OUTPUT_DIR = "data/combined"
REPORTS_DIR = "reports"

# Ordered list matching the EDA analysis order
SOURCE_FILES = [
    ("Monday-WorkingHours.pcap_ISCX.csv", "Monday"),
    ("Tuesday-WorkingHours.pcap_ISCX.csv", "Tuesday"),
    ("Wednesday-workingHours.pcap_ISCX.csv", "Wednesday"),
    ("Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv", "Thursday-Morning"),
    ("Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv", "Thursday-Afternoon"),
    ("Friday-WorkingHours-Morning.pcap_ISCX.csv", "Friday-Morning"),
    ("Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv", "Friday-PortScan"),
    ("Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv", "Friday-DDoS"),
]

# Expected row counts from individual EDA (validated)
EXPECTED_ROW_COUNTS = {
    "Monday-WorkingHours.pcap_ISCX.csv": 529918,
    "Tuesday-WorkingHours.pcap_ISCX.csv": 445909,
    "Wednesday-workingHours.pcap_ISCX.csv": 692703,
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": 170366,
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": 288602,
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": 191033,
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": 286467,
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": 225745,
}

EXPECTED_TOTAL_ROWS = 2830743

# Label normalization mapping for Thursday Web Attacks
# The raw CSV contains UTF-8 bytes EF BF BD (U+FFFD, Unicode Replacement Character)
# which is the result of a double-encoding artifact from CICFlowMeter's export.
# When read with UTF-8: labels contain \ufffd
# When read with latin-1: labels contain the 3-char sequence \xef\xbf\xbd  
# We handle BOTH cases for robustness.
WEB_ATTACK_LABEL_FIXES = {
    # UTF-8 read variant (U+FFFD replacement character)
    'Web Attack \ufffd Brute Force': 'Web Attack - Brute Force',
    'Web Attack \ufffd XSS': 'Web Attack - XSS',
    'Web Attack \ufffd Sql Injection': 'Web Attack - Sql Injection',
    # Windows-1252 raw byte variant (0x96 en-dash)
    'Web Attack \x96 Brute Force': 'Web Attack - Brute Force',
    'Web Attack \x96 XSS': 'Web Attack - XSS',
    'Web Attack \x96 Sql Injection': 'Web Attack - Sql Injection',
}

# Known expected label distribution (from CROSS_DATASET_ANALYSIS.md)
EXPECTED_LABEL_COUNTS = {
    "BENIGN": 2273097,
    "DoS Hulk": 231073,
    "PortScan": 158930,
    "DDoS": 128027,
    "DoS GoldenEye": 10293,
    "FTP-Patator": 7938,
    "SSH-Patator": 5897,
    "DoS slowloris": 5796,
    "DoS Slowhttptest": 5499,
    "Bot": 1966,
    "Web Attack - Brute Force": 1507,
    "Web Attack - XSS": 652,
    "Infiltration": 36,
    "Web Attack - Sql Injection": 21,
    "Heartbleed": 11,
}


def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536 * 16), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def harmonize_schema(df, filename, day_label):
    """
    Apply schema harmonization to a single dataset DataFrame.
    
    Operations (in order):
    1. Strip whitespace from column names
    2. Drop duplicate 'Fwd Header Length' column (index 34 -> 'Fwd Header Length.1')
    3. Strip whitespace from Label column
    4. Normalize Web Attack label encoding artifacts
    5. Add provenance columns
    """
    original_rows = len(df)
    
    # 1. Strip whitespace from column headers
    df.columns = df.columns.str.strip()
    
    # 2. Drop duplicate column 'Fwd Header Length.1' (original index 34)
    #    After stripping, pandas renames the second occurrence to 'Fwd Header Length.1'
    if 'Fwd Header Length.1' in df.columns:
        df = df.drop(columns=['Fwd Header Length.1'])
    
    # 3. Strip whitespace from Label values
    df['Label'] = df['Label'].astype(str).str.strip()
    
    # 4. Normalize Web Attack labels (Thursday Morning only has these, but apply globally for safety)
    for raw_label, clean_label in WEB_ATTACK_LABEL_FIXES.items():
        df['Label'] = df['Label'].replace(raw_label, clean_label)
    
    # Catch-all: replace any remaining non-ASCII characters in Web Attack labels with dash
    def normalize_web_attack(label):
        if 'Web Attack' in label and label not in ('Web Attack - Brute Force', 'Web Attack - XSS', 'Web Attack - Sql Injection'):
            # Replace any non-ASCII separator between 'Web Attack' and the attack type
            return re.sub(r'Web Attack\s*[^\w\s-]+\s*', 'Web Attack - ', label)
        return label
    df['Label'] = df['Label'].apply(normalize_web_attack)
    
    # 5. Add provenance columns
    df['Source_File'] = filename
    df['Source_Day'] = day_label
    df['Source_Row_Index'] = range(original_rows)
    
    assert len(df) == original_rows, f"Row count changed during harmonization for {filename}!"
    
    return df


def main():
    print("=" * 70)
    print("PHASE 2-4: CONTROLLED DATASET INTEGRATION")
    print(f"Timestamp: {datetime.datetime.now().isoformat()}")
    print("=" * 70)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # ============================================================
    # PHASE 2: Load & Harmonize Each Dataset
    # ============================================================
    print("\n--- PHASE 2: Schema Harmonization ---")
    
    all_dfs = []
    per_file_stats = []
    
    for filename, day_label in SOURCE_FILES:
        filepath = os.path.join(DATASET_DIR, filename)
        print(f"\n  Loading: {filename}...")
        
        # Load with explicit encoding handling for Web Attack labels
        try:
            df = pd.read_csv(filepath, encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='latin-1', low_memory=False)
        
        raw_rows = len(df)
        raw_cols = len(df.columns)
        expected_rows = EXPECTED_ROW_COUNTS[filename]
        
        # Validate raw row count
        if raw_rows != expected_rows:
            print(f"  [CRITICAL] ROW COUNT MISMATCH!")
            print(f"    Expected: {expected_rows:,}")
            print(f"    Actual:   {raw_rows:,}")
            sys.exit(1)
        
        print(f"    Raw: {raw_rows:,} rows x {raw_cols} columns [OK]")
        
        # Get raw label distribution BEFORE harmonization
        raw_labels = df.iloc[:, -1].astype(str).str.strip().value_counts().to_dict()
        
        # Apply schema harmonization
        df = harmonize_schema(df, filename, day_label)
        
        harmonized_cols = len(df.columns)  # Should be 78 features + 3 provenance = 81 (or 78-1+3=80 after dropping dup)
        harmonized_labels = df['Label'].value_counts().to_dict()
        
        print(f"    Harmonized: {len(df):,} rows x {harmonized_cols} columns")
        print(f"    Labels: {harmonized_labels}")
        
        per_file_stats.append({
            "filename": filename,
            "day_label": day_label,
            "raw_rows": raw_rows,
            "raw_cols": raw_cols,
            "harmonized_cols": harmonized_cols,
            "raw_labels": raw_labels,
            "harmonized_labels": harmonized_labels,
        })
        
        all_dfs.append(df)
    
    # ============================================================
    # PHASE 3: Controlled Concatenation
    # ============================================================
    print("\n\n--- PHASE 3: Controlled Concatenation ---")
    
    # Verify all DataFrames have identical column schemas before concat
    reference_cols = list(all_dfs[0].columns)
    for i, (filename, _) in enumerate(SOURCE_FILES):
        current_cols = list(all_dfs[i].columns)
        if current_cols != reference_cols:
            print(f"[CRITICAL] Schema mismatch in {filename}!")
            print(f"  Reference columns: {reference_cols}")
            print(f"  Current columns:   {current_cols}")
            diff_missing = set(reference_cols) - set(current_cols)
            diff_extra = set(current_cols) - set(reference_cols)
            if diff_missing:
                print(f"  Missing: {diff_missing}")
            if diff_extra:
                print(f"  Extra:   {diff_extra}")
            sys.exit(1)
    
    print(f"  Schema verified: All 8 datasets have {len(reference_cols)} identical columns.")
    
    # Concatenate
    df_combined = pd.concat(all_dfs, axis=0, ignore_index=True)
    
    print(f"  Combined shape: {df_combined.shape[0]:,} rows x {df_combined.shape[1]} columns")
    
    # ============================================================
    # PHASE 4: Validation
    # ============================================================
    print("\n\n--- PHASE 4: Combined Dataset Validation ---")
    
    # 4a: Total row count validation
    actual_total = len(df_combined)
    print(f"\n  [4a] Total Row Count:")
    print(f"    Expected: {EXPECTED_TOTAL_ROWS:,}")
    print(f"    Actual:   {actual_total:,}")
    if actual_total != EXPECTED_TOTAL_ROWS:
        print(f"    [CRITICAL] MISMATCH!")
        sys.exit(1)
    else:
        print(f"    [OK] MATCH")
    
    # 4b: Per-source row count validation
    print(f"\n  [4b] Per-Source Row Count Validation:")
    source_counts = df_combined['Source_File'].value_counts().to_dict()
    all_source_ok = True
    for filename, expected in EXPECTED_ROW_COUNTS.items():
        actual = source_counts.get(filename, 0)
        status = "[OK]" if actual == expected else "[FAIL]"
        if actual != expected:
            all_source_ok = False
        print(f"    {status} {filename}: {actual:,} (expected {expected:,})")
    
    if not all_source_ok:
        print("  [CRITICAL] Per-source row counts do not match!")
        sys.exit(1)
    
    # 4c: Global label distribution validation
    print(f"\n  [4c] Global Label Distribution Validation:")
    actual_labels = df_combined['Label'].value_counts().to_dict()
    
    all_label_ok = True
    for label, expected_count in sorted(EXPECTED_LABEL_COUNTS.items(), key=lambda x: -x[1]):
        actual_count = actual_labels.get(label, 0)
        status = "[OK]" if actual_count == expected_count else "[FAIL]"
        if actual_count != expected_count:
            all_label_ok = False
            print(f"    {status} {label}: {actual_count:,} (expected {expected_count:,}) DELTA={actual_count - expected_count}")
        else:
            print(f"    {status} {label}: {actual_count:,}")
    
    # Check for unexpected labels
    unexpected_labels = set(actual_labels.keys()) - set(EXPECTED_LABEL_COUNTS.keys())
    if unexpected_labels:
        print(f"\n    [WARNING] Unexpected labels found: {unexpected_labels}")
        for ul in unexpected_labels:
            print(f"      '{ul}' (count={actual_labels[ul]}, hex={ul.encode('utf-8').hex()})")
        all_label_ok = False
    
    if not all_label_ok:
        print("\n  [WARNING] Label distribution has discrepancies. Investigating...")
        # Print all unique labels with hex for debugging
        print("\n  All unique labels (with hex):")
        for label in sorted(df_combined['Label'].unique()):
            count = actual_labels.get(label, 0)
            hex_repr = label.encode('utf-8').hex()
            print(f"    '{label}' (count={count:,}, hex={hex_repr})")
    
    # 4d: Provenance integrity check
    print(f"\n  [4d] Provenance Integrity:")
    # Every row should have a valid Source_File and Source_Row_Index
    null_source = df_combined['Source_File'].isna().sum()
    null_idx = df_combined['Source_Row_Index'].isna().sum()
    print(f"    Null Source_File: {null_source}")
    print(f"    Null Source_Row_Index: {null_idx}")
    if null_source > 0 or null_idx > 0:
        print("    [CRITICAL] Provenance corruption detected!")
        sys.exit(1)
    else:
        print("    [OK] Full provenance intact")
    
    # 4e: Data type summary
    print(f"\n  [4e] Data Type Summary:")
    dtype_counts = df_combined.dtypes.value_counts()
    for dtype, count in dtype_counts.items():
        print(f"    {dtype}: {count} columns")
    
    # 4f: Missing/Infinite value summary
    print(f"\n  [4f] Data Quality Summary:")
    nan_total = df_combined.isna().sum().sum()
    print(f"    Total NaN values: {nan_total:,}")
    
    # Check for inf values in numeric columns
    numeric_cols = df_combined.select_dtypes(include=[np.number]).columns
    inf_total = np.isinf(df_combined[numeric_cols]).sum().sum()
    print(f"    Total Inf values: {inf_total:,}")
    
    # Identify which columns have inf
    inf_cols = {}
    for col in numeric_cols:
        inf_count = np.isinf(df_combined[col]).sum()
        if inf_count > 0:
            inf_cols[col] = int(inf_count)
    if inf_cols:
        print(f"    Columns with Inf: {inf_cols}")
    
    # 4g: Duplicate row analysis (excluding provenance columns)
    print(f"\n  [4g] Duplicate Row Analysis:")
    feature_cols = [c for c in df_combined.columns if c not in ['Source_File', 'Source_Day', 'Source_Row_Index']]
    dup_count = df_combined.duplicated(subset=feature_cols, keep=False).sum()
    print(f"    Duplicate rows (all feature+label cols): {dup_count:,} ({dup_count/actual_total*100:.2f}%)")
    
    # ============================================================
    # SAVE COMBINED DATASET
    # ============================================================
    print(f"\n\n--- SAVING COMBINED DATASET ---")
    
    output_path = os.path.join(OUTPUT_DIR, "CICIDS2017_COMBINED_RAW.csv")
    print(f"  Saving to: {output_path}")
    print(f"  Shape: {df_combined.shape}")
    df_combined.to_csv(output_path, index=False)
    
    output_size = os.path.getsize(output_path)
    output_hash = compute_sha256(output_path)
    
    print(f"  File size: {output_size:,} bytes ({output_size / (1024**3):.2f} GB)")
    print(f"  SHA-256: {output_hash}")
    
    # ============================================================
    # GENERATE MANIFEST
    # ============================================================
    manifest = {
        "artifact": "CICIDS2017_COMBINED_RAW.csv",
        "created": datetime.datetime.now().isoformat(),
        "description": "Controlled combination of all 8 CICIDS2017 CSV datasets with schema harmonization and provenance tracking",
        "total_rows": actual_total,
        "total_columns": df_combined.shape[1],
        "feature_columns": len(feature_cols),
        "provenance_columns": ["Source_File", "Source_Day", "Source_Row_Index"],
        "schema_harmonization": {
            "column_whitespace_stripped": True,
            "duplicate_column_dropped": "Fwd Header Length.1 (original index 34)",
            "label_whitespace_stripped": True,
            "web_attack_labels_normalized": True,
        },
        "source_files": [
            {
                "filename": stats["filename"],
                "day_label": stats["day_label"],
                "rows": stats["raw_rows"],
            }
            for stats in per_file_stats
        ],
        "label_distribution": {k: int(v) for k, v in sorted(actual_labels.items(), key=lambda x: -x[1])},
        "data_quality": {
            "total_nan": int(nan_total),
            "total_inf": int(inf_total),
            "inf_columns": inf_cols,
            "duplicate_rows": int(dup_count),
            "duplicate_pct": round(dup_count / actual_total * 100, 2),
        },
        "output": {
            "path": output_path,
            "size_bytes": output_size,
            "sha256": output_hash,
        }
    }
    
    manifest_path = os.path.join(OUTPUT_DIR, "MANIFEST.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n  Manifest saved: {manifest_path}")
    
    # ============================================================
    # FINAL VERDICT
    # ============================================================
    print("\n" + "=" * 70)
    if all_label_ok:
        print("COMBINED DATASET INTEGRATION: ALL VALIDATIONS PASSED")
    else:
        print("COMBINED DATASET INTEGRATION: COMPLETED WITH LABEL WARNINGS")
        print("  (Investigate label encoding discrepancies before proceeding)")
    print(f"  Total rows: {actual_total:,}")
    print(f"  Total columns: {df_combined.shape[1]}")
    print(f"  Unique labels: {len(actual_labels)}")
    print(f"  Output: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
