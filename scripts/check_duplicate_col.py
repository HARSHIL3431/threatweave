import os
import pandas as pd

dataset_dir = "dataset"
files = sorted([f for f in os.listdir(dataset_dir) if f.endswith(".csv")])

for filename in files:
    filepath = os.path.join(dataset_dir, filename)
    df = pd.read_csv(filepath, encoding='latin1', low_memory=False)
    # The two columns are at iloc[:, 14] and iloc[:, 34] or iloc[:, 34] and iloc[:, 55]? Let's check their names:
    col_names = df.columns
    fwd_hdr_cols = [c for c in col_names if 'fwd header length' in c.lower()]
    print(f"\n{filename}:")
    print(f"  Fwd Header Length columns found: {fwd_hdr_cols}")
    if len(fwd_hdr_cols) >= 2:
        c1 = df[fwd_hdr_cols[0]]
        c2 = df[fwd_hdr_cols[1]]
        identical = bool((c1 == c2).all())
        print(f"  Col 1: {repr(fwd_hdr_cols[0])} | Col 2: {repr(fwd_hdr_cols[1])} | All rows identical: {identical}")
