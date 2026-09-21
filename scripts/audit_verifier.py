import os
import sys
import json
import numpy as np
import pandas as pd

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("Running rigorous numerical re-verification across all datasets for Final Audit...")

dataset_dir = "dataset"
files = [
    ("Monday", "Monday-WorkingHours.pcap_ISCX.csv"),
    ("Tuesday", "Tuesday-WorkingHours.pcap_ISCX.csv"),
    ("Wednesday", "Wednesday-workingHours.pcap_ISCX.csv"),
    ("Thursday-Morning", "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"),
    ("Thursday-Afternoon", "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv"),
    ("Friday-Morning", "Friday-WorkingHours-Morning.pcap_ISCX.csv"),
    ("Friday-PortScan", "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"),
    ("Friday-DDoS", "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv")
]

audit_results = {}

for day, filename in files:
    filepath = os.path.join(dataset_dir, filename)
    df = pd.read_csv(filepath, encoding='latin1', low_memory=False)
    
    # Check duplicate columns exact equality across ALL rows
    raw_header = list(df.columns)
    stripped_header = [c.strip() for c in raw_header]
    
    fwd_hdr_indices = [i for i, c in enumerate(stripped_header) if c == 'Fwd Header Length']
    if len(fwd_hdr_indices) == 2:
        col1 = df.iloc[:, fwd_hdr_indices[0]]
        col2 = df.iloc[:, fwd_hdr_indices[1]]
        all_rows_identical = bool((col1 == col2).all())
    else:
        all_rows_identical = None
        
    df.columns = stripped_header
    # Fix duplicate column name for pandas indexing
    cols = list(df.columns)
    if cols.count('Fwd Header Length') > 1:
        first_idx = cols.index('Fwd Header Length')
        second_idx = cols.index('Fwd Header Length', first_idx + 1)
        cols[second_idx] = 'Fwd Header Length.1'
        df.columns = cols
        
    total_rows = len(df)
    dup_rows = int(df.duplicated().sum())
    
    # Label counts
    label_col = [c for c in df.columns if 'label' in c.lower()][0]
    label_counts = df[label_col].value_counts().to_dict()
    
    # Check Infs and duration == 0
    df['Flow Packets/s'] = pd.to_numeric(df['Flow Packets/s'], errors='coerce')
    df['Flow Bytes/s'] = pd.to_numeric(df['Flow Bytes/s'], errors='coerce')
    df['Flow Duration'] = pd.to_numeric(df['Flow Duration'], errors='coerce')
    
    inf_pkts = int(np.isinf(df['Flow Packets/s']).sum())
    inf_bytes = int(np.isinf(df['Flow Bytes/s']).sum())
    nan_bytes = int(df['Flow Bytes/s'].isna().sum())
    
    inf_mask = np.isinf(df['Flow Packets/s']) | np.isinf(df['Flow Bytes/s'])
    inf_total = int(inf_mask.sum())
    inf_zero_dur = int(((df['Flow Duration'] == 0) & inf_mask).sum())
    
    audit_results[day] = {
        "filename": filename,
        "rows": total_rows,
        "duplicate_rows": dup_rows,
        "dup_cols_identical_all_rows": all_rows_identical,
        "nan_bytes": nan_bytes,
        "inf_pkts": inf_pkts,
        "inf_bytes": inf_bytes,
        "inf_total": inf_total,
        "inf_zero_dur": inf_zero_dur,
        "inf_zero_dur_pct": round(inf_zero_dur / inf_total * 100, 2) if inf_total > 0 else 100.0,
        "labels": {str(k): int(v) for k, v in label_counts.items()}
    }

print("\n--- Numerical Re-Verification Results ---")
for k, v in audit_results.items():
    print(f"{k}: Rows={v['rows']:,}, Dups={v['duplicate_rows']:,}, NaNs={v['nan_bytes']:,}, Infs={v['inf_total']:,} (ZeroDur: {v['inf_zero_dur']}/{v['inf_total']} = {v['inf_zero_dur_pct']}%), DupColIdentical={v['dup_cols_identical_all_rows']}")
    print(f"   Labels: {v['labels']}")

with open("reports/audit_reverification.json", "w", encoding="utf-8") as f:
    json.dump(audit_results, f, indent=2)

print("\nAudit re-verification completed successfully.")
