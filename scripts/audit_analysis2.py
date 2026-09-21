"""
Additional audit analyses: skewness before/after log, correlation details, 
label conflict investigation, computational estimates.
"""
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r"C:\Users\Admin\Desktop\demo\data\combined\CICIDS2017_COMBINED_RAW.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, low_memory=False)

# Metadata/label columns
metadata_cols = ['Source_File', 'Source_Day', 'Source_Row_Index']
feature_cols = [c for c in df.columns if c not in metadata_cols and c != 'Label']
numeric_feats = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()

# ============================================================
# A. LOG TRANSFORMATION VALIDATION
# ============================================================
print("\n" + "=" * 80)
print("[A] LOG TRANSFORMATION VALIDATION")
print("=" * 80)

# Check which heavy-tailed features can safely use log1p
heavy_tailed = ['Flow Duration', 'Flow Bytes/s', 'Flow Packets/s',
                'Total Fwd Packets', 'Total Backward Packets',
                'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
                'Flow IAT Mean', 'Flow IAT Max', 'Flow IAT Std',
                'Fwd IAT Total', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max',
                'Bwd IAT Total', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max',
                'Fwd Packets/s', 'Bwd Packets/s',
                'Active Mean', 'Active Std', 'Active Max', 'Active Min',
                'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min',
                'act_data_pkt_fwd', 'min_seg_size_forward',
                'Fwd Header Length', 'Bwd Header Length',
                'Total Length of Fwd Packets', 'Total Length of Bwd Packets']

# Only check features that exist
heavy_tailed = [f for f in heavy_tailed if f in df.columns]
# Deduplicate
heavy_tailed = list(dict.fromkeys(heavy_tailed))

print(f"\n{'Feature':<35s} {'Min':>15s} {'Has Neg':>8s} {'Zero%':>7s} {'Skew':>10s} {'log1p valid?':>12s}")
print("-" * 95)

for feat in heavy_tailed:
    s = df[feat].dropna()
    min_val = s.min()
    has_neg = min_val < 0
    zero_pct = (s == 0).mean() * 100
    skew = s.skew()
    
    if has_neg:
        valid = "NO (neg)"
    elif min_val < 0:
        valid = "NO (<0)" 
    else:
        valid = "YES"
    
    print(f"{feat:<35s} {min_val:>15.2f} {str(has_neg):>8s} {zero_pct:>6.1f}% {skew:>10.2f} {valid:>12s}")

# Check features with negative values that need special treatment
print("\n\nFeatures with negative values requiring signed-log or other treatment:")
neg_feats = []
for feat in numeric_feats:
    s = df[feat].dropna()
    if s.min() < 0:
        neg_feats.append(feat)
        print(f"  {feat}: min={s.min():.2f}, skew={s.skew():.2f}")

# ============================================================
# B. LABEL CONFLICT DEEP DIVE
# ============================================================
print("\n" + "=" * 80)
print("[B] LABEL CONFLICT DEEP DIVE")
print("=" * 80)

# Get all conflicting feature vectors
conflict_info = []
for feat_vals, group in df.groupby(feature_cols):
    labels = group['Label'].unique()
    if len(labels) > 1:
        conflict_info.append({
            'labels': sorted(labels.tolist()),
            'count': len(group),
            'days': group['Source_Day'].value_counts().to_dict()
        })

# Summarize by label pair
from collections import Counter
pair_counter = Counter()
for ci in conflict_info:
    pair_key = tuple(ci['labels'])
    pair_counter[pair_key] += 1

print(f"\nLabel conflict pairs:")
for pair, count in pair_counter.most_common():
    print(f"  {pair}: {count} conflicting feature vectors")

# ============================================================
# C. CORRELATION GROUPS (canonical representation)
# ============================================================
print("\n" + "=" * 80)
print("[C] CORRELATION GROUPS - CANONICAL REPRESENTATION")
print("=" * 80)

# Build correlation matrix on a sample
sample_size = min(200000, len(df))
sample = df[numeric_feats].sample(n=sample_size, random_state=42)
corr = sample.corr()

# Find perfect groups using graph clustering
groups = []
visited = set()
for i, f1 in enumerate(numeric_feats):
    if f1 in visited:
        continue
    group = [f1]
    visited.add(f1)
    for j, f2 in enumerate(numeric_feats):
        if f2 in visited:
            continue
        if abs(corr.loc[f1, f2]) >= 0.999:
            group.append(f2)
            visited.add(f2)
    if len(group) > 1:
        groups.append(group)

print(f"\nRedundant groups (|r| >= 0.999):")
for i, g in enumerate(groups):
    print(f"\n  Group {i+1}: {g}")
    # Determine canonical: prefer the more interpretable name
    # Simple heuristic: prefer names without 'Subflow', 'Avg', 'Segment'
    canonical = g[0]
    for f in g:
        if 'Subflow' not in f and 'Avg' not in f and 'Segment' not in f:
            canonical = f
            break
    print(f"    -> Retain: {canonical}")
    print(f"    -> Remove: {[f for f in g if f != canonical]}")

# ============================================================
# D. NaN AND INF CO-OCCURRENCE ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[D] NaN AND INF CO-OCCURRENCE ANALYSIS")
print("=" * 80)

# NaN in Flow Bytes/s
nan_mask = df['Flow Bytes/s'].isna()
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
zero_dur_mask = df['Flow Duration'] == 0

print(f"\nNaN rows (Flow Bytes/s): {nan_mask.sum()}")
print(f"Inf rows (Flow Bytes/s or Flow Packets/s): {inf_mask.sum()}")
print(f"Zero-duration rows: {zero_dur_mask.sum()}")

print(f"\nNaN AND zero-duration: {(nan_mask & zero_dur_mask).sum()}")
print(f"Inf AND zero-duration: {(inf_mask & zero_dur_mask).sum()}")
print(f"NaN AND Inf: {(nan_mask & inf_mask).sum()}")

# What's the relationship between NaN and Inf?
# NaN rows: Flow Bytes/s is NaN, what about Flow Packets/s?
nan_rows = df[nan_mask]
print(f"\nNaN rows - Flow Packets/s Inf: {np.isinf(nan_rows['Flow Packets/s']).sum()}")
print(f"NaN rows - Flow Packets/s NaN: {nan_rows['Flow Packets/s'].isna().sum()}")
print(f"NaN rows - Flow Packets/s finite: {np.isfinite(nan_rows['Flow Packets/s']).sum()}")

# Inf rows: Flow Bytes/s Inf vs NaN
inf_rows = df[inf_mask]
print(f"\nInf rows - Flow Bytes/s Inf: {np.isinf(inf_rows['Flow Bytes/s']).sum()}")
print(f"Inf rows - Flow Bytes/s NaN: {inf_rows['Flow Bytes/s'].isna().sum()}")

# ============================================================
# E. COMPUTATIONAL ESTIMATES
# ============================================================
print("\n" + "=" * 80)
print("[E] COMPUTATIONAL ESTIMATES")
print("=" * 80)

n_rows = len(df)
n_features = len(numeric_feats)

print(f"Total rows: {n_rows:,}")
print(f"Numeric features: {n_features}")
print(f"DataFrame RAM: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")
print(f"Correlation matrix ({n_features}x{n_features}) RAM: ~{n_features * n_features * 8 / 1e6:.1f} MB")
print(f"Isolation Forest estimates:")
print(f"  n_estimators=100, max_samples=256: ~{100 * 256 * n_features * 10 / 1e6:.0f}M node operations")
print(f"  n_estimators=100, max_samples=1024: ~{100 * 1024 * n_features * 10 / 1e6:.0f}M node operations")

# After deduplication estimate
n_unique = n_rows - 309079
print(f"\nAfter dedup: ~{n_unique:,} rows")
print(f"  DataFrame RAM estimate: ~{n_unique * n_features * 8 / 1e9:.2f} GB (numeric only)")

# Monday-only training set
monday_rows = df[df['Source_Day'] == 'Monday'].shape[0]
monday_benign = df[(df['Source_Day'] == 'Monday') & (df['Label'] == 'BENIGN')].shape[0]
print(f"\nMonday total: {monday_rows:,}")
print(f"Monday benign: {monday_benign:,}")
print(f"All-day benign: {df[df['Label'] == 'BENIGN'].shape[0]:,}")

# ============================================================
# F. FWD HEADER LENGTH NEGATIVE VALUES INVESTIGATION
# ============================================================
print("\n" + "=" * 80)
print("[F] NEGATIVE HEADER LENGTH INVESTIGATION")
print("=" * 80)

for feat in ['Fwd Header Length', 'Bwd Header Length', 'min_seg_size_forward']:
    if feat in df.columns:
        s = df[feat]
        neg_count = (s < 0).sum()
        print(f"\n{feat}:")
        print(f"  Negative values: {neg_count} ({neg_count/len(df)*100:.4f}%)")
        print(f"  Min: {s.min():.0f}")
        print(f"  Max: {s.max():.0f}")
        if neg_count > 0:
            neg_rows = df[s < 0]
            print(f"  Label distribution of negative rows:")
            print(f"    {neg_rows['Label'].value_counts().to_dict()}")
            print(f"  Source_Day distribution of negative rows:")
            print(f"    {neg_rows['Source_Day'].value_counts().to_dict()}")

print("\n\nANALYSIS COMPLETE")
