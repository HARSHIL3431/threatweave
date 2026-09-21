"""
CICIDS2017 Final Preprocessing Design Audit - Data Analysis Script
Read-only analyses to verify claims and gather evidence.
"""
import pandas as pd
import numpy as np
import json
import os
import sys
import warnings
warnings.filterwarnings('ignore')

DATA_PATH = r"C:\Users\Admin\Desktop\demo\data\combined\CICIDS2017_COMBINED_RAW.csv"
REPORTS_PATH = r"C:\Users\Admin\Desktop\demo\reports"

print("=" * 80)
print("CICIDS2017 PREPROCESSING DESIGN AUDIT - DATA ANALYSIS")
print("=" * 80)

# ============================================================
# 1. LOAD DATA AND BASIC METADATA
# ============================================================
print("\n[1] Loading combined dataset...")
df = pd.read_csv(DATA_PATH, low_memory=False)
print(f"   Shape: {df.shape}")
print(f"   Columns: {list(df.columns)}")

# Identify metadata vs feature columns
metadata_cols = ['Source_File', 'Source_Day', 'Source_Row_Index']
label_cols = [c for c in df.columns if 'label' in c.lower() or c in ['Label', 'Binary_Label', 'Normalized_Label', 'Original_Label']]
feature_cols = [c for c in df.columns if c not in metadata_cols and c not in label_cols]

print(f"\n   Metadata columns: {metadata_cols}")
print(f"   Label columns found: {[c for c in df.columns if c in label_cols or 'label' in c.lower()]}")
print(f"   Feature columns: {len(feature_cols)}")
print(f"   First 5 feature cols: {feature_cols[:5]}")

# Check for Source_Day and Source_File
if 'Source_Day' in df.columns:
    print(f"\n   Source_Day values: {df['Source_Day'].value_counts().to_dict()}")
if 'Source_File' in df.columns:
    print(f"\n   Source_File values: {df['Source_File'].value_counts().to_dict()}")

# ============================================================
# 2. LABEL ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[2] LABEL ANALYSIS")
print("=" * 80)

label_col = 'Label' if 'Label' in df.columns else None
if label_col is None:
    for c in df.columns:
        if 'label' in c.lower():
            label_col = c
            break

if label_col:
    print(f"\n   Using label column: {label_col}")
    print(f"\n   Label distribution:")
    label_dist = df[label_col].value_counts()
    for label, count in label_dist.items():
        pct = count / len(df) * 100
        print(f"   {label:40s} {count:>10d} ({pct:.4f}%)")
    
    # Binary label
    binary_label = (df[label_col] != 'BENIGN').astype(int)
    print(f"\n   Binary: Benign={binary_label.sum() == 0} Count={(binary_label == 0).sum()}, Attack Count={(binary_label == 1).sum()}, Attack%={binary_label.mean()*100:.2f}%")
else:
    print("   ERROR: No label column found!")
    print(f"   Available columns: {list(df.columns)}")

# ============================================================
# 3. DUPLICATE ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[3] DUPLICATE ANALYSIS")
print("=" * 80)

# Use feature columns only (excluding metadata and labels)
numeric_features = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
print(f"\n   Numeric feature columns for duplicate detection: {len(numeric_features)}")

# Exact duplicates on all feature columns
dup_mask = df.duplicated(subset=feature_cols, keep=False)
n_total_dups = df.duplicated(subset=feature_cols, keep='first').sum()
print(f"   Total duplicate rows (keep=first): {n_total_dups} ({n_total_dups/len(df)*100:.2f}%)")

# Duplicate groups
dup_groups = df.groupby(feature_cols).size()
dup_groups_multi = dup_groups[dup_groups > 1]
print(f"   Number of duplicate groups: {len(dup_groups_multi)}")
print(f"   Rows in duplicate groups: {dup_groups_multi.sum()}")

# Inter-dataset duplicates
if 'Source_Day' in df.columns:
    # Groups where duplicates span different days
    inter_dup_count = 0
    intra_dup_count = 0
    for feat_vals, group in df.groupby(feature_cols):
        if len(group) > 1:
            days = group['Source_Day'].nunique()
            dup_rows = len(group) - 1  # extra copies
            if days > 1:
                inter_dup_count += dup_rows
            else:
                intra_dup_count += dup_rows
    print(f"\n   Inter-dataset duplicates (across days): {inter_dup_count}")
    print(f"   Intra-dataset duplicates (same day): {intra_dup_count}")

# ============================================================
# 4. LABEL CONFLICT ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[4] LABEL CONFLICT ANALYSIS")
print("=" * 80)

if label_col:
    conflict_groups = 0
    conflict_rows = 0
    conflict_examples = []
    
    for feat_vals, group in df.groupby(feature_cols):
        unique_labels = group[label_col].nunique()
        if unique_labels > 1:
            conflict_groups += 1
            conflict_rows += len(group)
            if len(conflict_examples) < 5:
                conflict_examples.append({
                    'labels': group[label_col].unique().tolist(),
                    'count': len(group),
                    'source_days': group['Source_Day'].value_counts().to_dict() if 'Source_Day' in df.columns else 'N/A'
                })
    
    print(f"   Conflicting feature vectors: {conflict_groups}")
    print(f"   Total rows with label conflicts: {conflict_rows}")
    print(f"\n   Example conflicts:")
    for i, ex in enumerate(conflict_examples):
        print(f"   [{i+1}] Labels: {ex['labels']}, Count: {ex['count']}, Days: {ex['source_days']}")

# ============================================================
# 5. ZERO-DURATION / INF ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[5] ZERO-DURATION / INF ANALYSIS")
print("=" * 80)

if 'Flow Duration' in df.columns:
    zero_dur = df[df['Flow Duration'] == 0]
    print(f"   Zero-duration flows: {len(zero_dur)}")
    
    if label_col:
        print(f"\n   Label distribution of zero-duration flows:")
        zd_labels = zero_dur[label_col].value_counts()
        for label, count in zd_labels.items():
            print(f"   {label:40s} {count:>8d}")
    
    # Check Inf in rate features
    for feat in ['Flow Bytes/s', 'Flow Packets/s']:
        if feat in df.columns:
            inf_count = np.isinf(df[feat]).sum()
            print(f"\n   {feat} Inf count: {inf_count}")
            # Check NaN
            nan_count = df[feat].isna().sum()
            print(f"   {feat} NaN count: {nan_count}")
    
    # Are NaN rows also zero-duration?
    if 'Flow Bytes/s' in df.columns:
        nan_rows = df[df['Flow Bytes/s'].isna()]
        if len(nan_rows) > 0:
            nan_zero_dur = (nan_rows['Flow Duration'] == 0).sum()
            print(f"\n   NaN rows with zero duration: {nan_zero_dur}/{len(nan_rows)}")
    
    # Zero duration by source day
    if 'Source_Day' in df.columns:
        print(f"\n   Zero-duration by Source_Day:")
        zd_day = zero_dur['Source_Day'].value_counts()
        for day, count in zd_day.items():
            print(f"   {day:30s} {count:>8d}")

# ============================================================
# 6. CONSTANT FEATURES
# ============================================================
print("\n" + "=" * 80)
print("[6] CONSTANT FEATURES ANALYSIS")
print("=" * 80)

const_features = []
for col in feature_cols:
    if col in df.columns:
        unique_vals = df[col].nunique()
        if unique_vals <= 1:
            const_features.append((col, df[col].iloc[0] if len(df) > 0 else None))
        elif unique_vals <= 3:
            val_counts = df[col].value_counts()
            top_pct = val_counts.iloc[0] / len(df) * 100
            if top_pct > 99.9:
                const_features.append((col, f"nearly constant: {val_counts.index[0]} ({top_pct:.2f}%)"))

print(f"   Constant/nearly-constant features: {len(const_features)}")
for feat, val in const_features:
    print(f"   {feat:40s} -> {val}")

# ============================================================
# 7. CORRELATION / REDUNDANCY ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[7] CORRELATION / REDUNDANCY ANALYSIS")
print("=" * 80)

# Select only numeric feature columns for correlation
numeric_feats = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()
print(f"   Numeric features for correlation: {len(numeric_feats)}")

if len(numeric_feats) > 0 and len(numeric_feats) < 200:
    # Sample for speed if needed
    sample_size = min(100000, len(df))
    corr_sample = df[numeric_feats].sample(n=sample_size, random_state=42)
    corr_matrix = corr_sample.corr()
    
    # Find perfect/near-perfect correlations
    perfect_pairs = []
    for i in range(len(numeric_feats)):
        for j in range(i+1, len(numeric_feats)):
            r = abs(corr_matrix.iloc[i, j])
            if r >= 0.999:
                perfect_pairs.append((numeric_feats[i], numeric_feats[j], corr_matrix.iloc[i, j]))
    
    print(f"\n   Perfectly correlated pairs (|r| >= 0.999): {len(perfect_pairs)}")
    for f1, f2, r in perfect_pairs:
        print(f"   {f1:40s} <-> {f2:40s} r={r:.6f}")
    
    # High correlations (0.90-0.999)
    high_pairs = []
    for i in range(len(numeric_feats)):
        for j in range(i+1, len(numeric_feats)):
            r = abs(corr_matrix.iloc[i, j])
            if 0.90 <= r < 0.999:
                high_pairs.append((numeric_feats[i], numeric_feats[j], corr_matrix.iloc[i, j]))
    
    print(f"\n   Highly correlated pairs (0.90 <= |r| < 0.999): {len(high_pairs)}")
    for f1, f2, r in high_pairs[:20]:  # show first 20
        print(f"   {f1:40s} <-> {f2:40s} r={r:.6f}")
    if len(high_pairs) > 20:
        print(f"   ... and {len(high_pairs)-20} more pairs")

# ============================================================
# 8. FEATURE DISTRIBUTIONS FOR TRANSFORMATION
# ============================================================
print("\n" + "=" * 80)
print("[8] FEATURE DISTRIBUTIONS - TRANSFORMATION AUDIT")
print("=" * 80)

# Check skewness and min values for numeric features
skew_data = []
for col in numeric_feats:
    if col in df.columns:
        series = df[col].dropna()
        if len(series) > 0 and series.std() > 0:
            skew_val = series.skew()
            min_val = series.min()
            has_neg = (series < 0).any()
            zero_pct = (series == 0).mean() * 100
            max_val = series.max()
            skew_data.append({
                'feature': col,
                'skewness': skew_val,
                'min': min_val,
                'max': max_val,
                'has_negative': has_neg,
                'zero_pct': zero_pct
            })

# Sort by absolute skewness
skew_data.sort(key=lambda x: abs(x['skewness']), reverse=True)

print(f"\n   Features with |skewness| > 20 (heavy-tailed):")
heavy_tailed = [s for s in skew_data if abs(s['skewness']) > 20]
for s in heavy_tailed[:30]:
    neg_flag = "NEG" if s['has_negative'] else ""
    print(f"   {s['feature']:40s} skew={s['skewness']:>12.2f} min={s['min']:>15.2f} max={s['max']:>15.2f} zero%={s['zero_pct']:.1f}% {neg_flag}")

print(f"\n   Total heavy-tailed features (|skew|>20): {len(heavy_tailed)}")

# Features with negative values
neg_features = [s for s in skew_data if s['has_negative']]
print(f"\n   Features with negative values: {len(neg_features)}")
for s in neg_features[:15]:
    print(f"   {s['feature']:40s} min={s['min']:.4f}")

# ============================================================
# 9. DESTINATION PORT ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[9] DESTINATION PORT ANALYSIS")
print("=" * 80)

if 'Destination Port' in df.columns and label_col:
    print(f"\n   Top 20 Destination Ports by flow count:")
    port_label = df.groupby(['Destination Port', label_col]).size().reset_index(name='count')
    top_ports = df['Destination Port'].value_counts().head(20)
    for port, count in top_ports.items():
        # Get dominant label
        port_data = df[df['Destination Port'] == port]
        dominant_label = port_data[label_col].value_counts().index[0]
        dominant_pct = port_data[label_col].value_counts().iloc[0] / len(port_data) * 100
        print(f"   Port {port:>6d}: {count:>8d} flows, dominant={dominant_label:30s} ({dominant_pct:.1f}%)")
    
    # Check port-label association
    print(f"\n   Attack-specific port associations:")
    attacks = df[df[label_col] != 'BENIGN']
    for attack_type in attacks[label_col].unique():
        attack_data = attacks[attacks[label_col] == attack_type]
        top_port = attack_data['Destination Port'].value_counts().index[0]
        top_port_pct = attack_data['Destination Port'].value_counts().iloc[0] / len(attack_data) * 100
        print(f"   {attack_type:40s} -> Port {top_port:>6d} ({top_port_pct:.1f}%)")

# ============================================================
# 10. SOURCE-DAY LEAKAGE ANALYSIS
# ============================================================
print("\n" + "=" * 80)
print("[10] SOURCE-DAY LEAKAGE ANALYSIS")
print("=" * 80)

if 'Source_Day' in df.columns and label_col:
    print(f"\n   P(Attack | Source_Day):")
    for day in df['Source_Day'].unique():
        day_data = df[df['Source_Day'] == day]
        attack_pct = (day_data[label_col] != 'BENIGN').mean() * 100
        print(f"   {day:30s} Attack% = {attack_pct:.2f}%")
    
    print(f"\n   Class composition by day:")
    for day in sorted(df['Source_Day'].unique()):
        day_data = df[df['Source_Day'] == day]
        classes = day_data[label_col].value_counts()
        attack_classes = [f"{c}({n})" for c, n in classes.items() if c != 'BENIGN']
        print(f"   {day:30s} Attacks: {', '.join(attack_classes) if attack_classes else 'None'}")

# ============================================================
# 11. SEMI-CONSTANT FEATURES
# ============================================================
print("\n" + "=" * 80)
print("[11] SEMI-CONSTANT FEATURES")
print("=" * 80)

for col in feature_cols:
    if col in df.columns:
        unique_vals = df[col].nunique()
        if 2 <= unique_vals <= 5:
            val_counts = df[col].value_counts()
            top_pct = val_counts.iloc[0] / len(df) * 100
            if top_pct > 99.9:
                print(f"   {col:40s} unique={unique_vals}, top_value={val_counts.index[0]}, top%={top_pct:.4f}%")
                # Check which dataset has non-zero values
                if 'Source_Day' in df.columns:
                    nonzero = df[df[col] != val_counts.index[0]]
                    if len(nonzero) > 0 and len(nonzero) < 500:
                        print(f"     Non-zero occurrences: {len(nonzero)}, Source_Days: {nonzero['Source_Day'].value_counts().to_dict()}")

# ============================================================
# 12. COMPUTATIONAL METRICS
# ============================================================
print("\n" + "=" * 80)
print("[12] COMPUTATIONAL METRICS")
print("=" * 80)

print(f"   DataFrame memory usage: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")
print(f"   Per-row memory: {df.memory_usage(deep=True).sum() / len(df):.0f} bytes")
print(f"   Total rows: {len(df):,}")
print(f"   Total columns: {len(df.columns)}")
print(f"   Numeric columns: {len(df.select_dtypes(include=[np.number]).columns)}")

# ============================================================
# 13. NaN PATTERN ANALYSIS  
# ============================================================
print("\n" + "=" * 80)
print("[13] NaN PATTERN ANALYSIS")
print("=" * 80)

nan_cols = df.columns[df.isna().any()].tolist()
print(f"   Columns with NaN: {nan_cols}")
for col in nan_cols:
    nan_count = df[col].isna().sum()
    nan_pct = nan_count / len(df) * 100
    print(f"   {col:40s} NaN: {nan_count} ({nan_pct:.4f}%)")
    
    # Check if NaN rows overlap with zero-duration
    nan_rows = df[df[col].isna()]
    if 'Flow Duration' in df.columns:
        overlap_zero_dur = (nan_rows['Flow Duration'] == 0).sum()
        print(f"     Overlap with Flow Duration==0: {overlap_zero_dur}/{len(nan_rows)}")
    
    # Check label distribution of NaN rows
    if label_col:
        nan_labels = nan_rows[label_col].value_counts()
        print(f"     Labels: {dict(nan_labels)}")

# ============================================================
# 14. CHECK FOR Fwd Header Length.1 duplicate column
# ============================================================
print("\n" + "=" * 80)
print("[14] DUPLICATE COLUMN CHECK")
print("=" * 80)

if 'Fwd Header Length' in df.columns and 'Fwd Header Length.1' in df.columns:
    match = (df['Fwd Header Length'] == df['Fwd Header Length.1']).all()
    print(f"   Fwd Header Length == Fwd Header Length.1: {match}")
elif 'Fwd Header Length.1' in df.columns:
    print("   Fwd Header Length.1 exists but Fwd Header Length not found by exact name")
    # Check similar names
    fwd_cols = [c for c in df.columns if 'Fwd Header' in c]
    print(f"   Columns with 'Fwd Header': {fwd_cols}")
else:
    print("   Fwd Header Length.1 not found (may already be removed)")
    fwd_cols = [c for c in df.columns if 'Fwd Header' in c]
    print(f"   Columns with 'Fwd Header': {fwd_cols}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
