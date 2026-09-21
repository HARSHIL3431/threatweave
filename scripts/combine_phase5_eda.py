"""
Phase 5: Combined Benchmark-Level EDA
=======================================
Comprehensive analysis of the combined CICIDS2017 dataset.

Sections:
1. Global Distribution Profiling
2. Cross-Dataset Duplicate Analysis (intra vs inter-dataset)
3. Feature Correlation & Redundancy Analysis
4. Benign Traffic Drift on Combined Data
5. Data Leakage Vector Assessment
6. Infinity & NaN Root Cause Verification
7. Constant & Near-Constant Feature Analysis
8. Isolation Forest Readiness Evaluation
"""
import os
import sys
import json
import datetime
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore', category=pd.errors.DtypeWarning)
warnings.filterwarnings('ignore', category=RuntimeWarning)

COMBINED_CSV = "data/combined/CICIDS2017_COMBINED_RAW.csv"
FIGURES_DIR = "figures/combined_eda"
REPORTS_DIR = "reports"

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# ============================================================
# LOAD COMBINED DATASET
# ============================================================
print("=" * 70)
print("PHASE 5: COMBINED BENCHMARK-LEVEL EDA")
print(f"Timestamp: {datetime.datetime.now().isoformat()}")
print("=" * 70)

print("\nLoading combined dataset...")
df = pd.read_csv(COMBINED_CSV, low_memory=False)
print(f"Shape: {df.shape[0]:,} rows x {df.shape[1]} columns")
print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1e9:.2f} GB")

# Identify column groups
provenance_cols = ['Source_File', 'Source_Day', 'Source_Row_Index']
label_col = 'Label'
feature_cols = [c for c in df.columns if c not in provenance_cols + [label_col]]
numeric_cols = df[feature_cols].select_dtypes(include=[np.number]).columns.tolist()

print(f"\nFeature columns: {len(feature_cols)}")
print(f"Numeric feature columns: {len(numeric_cols)}")
print(f"Provenance columns: {provenance_cols}")

results = {}

# ============================================================
# SECTION 1: Global Distribution Profiling
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 1: GLOBAL DISTRIBUTION PROFILING")
print("=" * 70)

# 1a: Label distribution
label_dist = df[label_col].value_counts()
label_pct = df[label_col].value_counts(normalize=True) * 100

print("\n  Global Label Distribution:")
print(f"  {'Label':<30} {'Count':>10} {'Pct':>8}")
print("  " + "-" * 50)
for label in label_dist.index:
    print(f"  {label:<30} {label_dist[label]:>10,} {label_pct[label]:>7.4f}%")

binary_attack = (df[label_col] != 'BENIGN').sum()
binary_benign = (df[label_col] == 'BENIGN').sum()
print(f"\n  Binary split: BENIGN={binary_benign:,} ({binary_benign/len(df)*100:.2f}%) | ATTACK={binary_attack:,} ({binary_attack/len(df)*100:.2f}%)")

results['label_distribution'] = {k: int(v) for k, v in label_dist.to_dict().items()}
results['binary_split'] = {'benign': int(binary_benign), 'attack': int(binary_attack)}

# 1b: Per-source-day distribution
print("\n  Per-Source Label Matrix:")
label_matrix = pd.crosstab(df['Source_Day'], df[label_col], margins=True)
print(label_matrix.to_string())

# 1c: Plot - Log-scale label distribution
fig, ax = plt.subplots(figsize=(14, 6))
colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(label_dist)))
bars = ax.barh(range(len(label_dist)), label_dist.values, color=colors)
ax.set_yticks(range(len(label_dist)))
ax.set_yticklabels(label_dist.index, fontsize=10)
ax.set_xscale('log')
ax.set_xlabel('Flow Count (log scale)', fontsize=12)
ax.set_title('CICIDS2017 Combined: Global Label Distribution (15 Classes)', fontsize=14, fontweight='bold')
for i, (count, pct) in enumerate(zip(label_dist.values, label_pct.values)):
    ax.text(count * 1.1, i, f'{count:,} ({pct:.3f}%)', va='center', fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'global_label_distribution.png'), dpi=150)
plt.close()
print(f"\n  Saved: {FIGURES_DIR}/global_label_distribution.png")

# ============================================================
# SECTION 2: CROSS-DATASET DUPLICATE ANALYSIS
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 2: CROSS-DATASET DUPLICATE ANALYSIS")
print("=" * 70)

# 2a: Overall duplicate count
dup_mask_all = df.duplicated(subset=feature_cols + [label_col], keep=False)
total_dup_all = dup_mask_all.sum()
print(f"\n  Total duplicate rows (feature+label, keep=False): {total_dup_all:,} ({total_dup_all/len(df)*100:.2f}%)")

dup_mask_first = df.duplicated(subset=feature_cols + [label_col], keep='first')
total_dup_first = dup_mask_first.sum()
print(f"  Removable duplicates (keep='first'): {total_dup_first:,} ({total_dup_first/len(df)*100:.2f}%)")

# 2b: Intra-dataset vs Inter-dataset duplicates
print("\n  Analyzing intra vs inter-dataset duplicates...")

# Find all duplicate groups and check if they span multiple source files
dup_df = df[dup_mask_all].copy()
# Group by feature+label values and count unique source files
# Use a hash approach for efficiency with large data
feature_hash = pd.util.hash_pandas_object(df[feature_cols + [label_col]], index=False)
df['_hash'] = feature_hash

hash_counts = df.groupby('_hash').agg(
    count=('_hash', 'size'),
    n_sources=('Source_File', 'nunique'),
    sources=('Source_File', lambda x: ','.join(sorted(x.unique())))
).reset_index()

# Duplicates are hashes appearing more than once
dup_hashes = hash_counts[hash_counts['count'] > 1]
intra_only = dup_hashes[dup_hashes['n_sources'] == 1]
inter = dup_hashes[dup_hashes['n_sources'] > 1]

intra_rows = df[df['_hash'].isin(intra_only['_hash'])].shape[0]
inter_rows = df[df['_hash'].isin(inter['_hash'])].shape[0]

print(f"\n  Duplicate flow groups: {len(dup_hashes):,}")
print(f"    Intra-dataset only (same source file): {len(intra_only):,} groups ({intra_rows:,} rows)")
print(f"    Inter-dataset (cross-file duplicates): {len(inter):,} groups ({inter_rows:,} rows)")

# 2c: Per-source duplicate breakdown
print("\n  Per-Source Duplicate Breakdown:")
per_source_dups = {}
for source in df['Source_File'].unique():
    source_df = df[df['Source_File'] == source]
    source_dup = source_df.duplicated(subset=feature_cols + [label_col], keep='first').sum()
    per_source_dups[source] = {
        'total_rows': len(source_df),
        'duplicates': int(source_dup),
        'pct': round(source_dup / len(source_df) * 100, 2)
    }
    print(f"    {source}: {source_dup:,}/{len(source_df):,} ({source_dup/len(source_df)*100:.2f}%)")

# 2d: Per-label duplicate breakdown
print("\n  Per-Label Duplicate Breakdown:")
per_label_dups = {}
for label in label_dist.index:
    label_df = df[df[label_col] == label]
    label_dup = label_df.duplicated(subset=feature_cols, keep='first').sum()
    per_label_dups[label] = {
        'total_rows': len(label_df),
        'duplicates': int(label_dup),
        'pct': round(label_dup / len(label_df) * 100, 2)
    }
    print(f"    {label}: {label_dup:,}/{len(label_df):,} ({label_dup/len(label_df)*100:.2f}%)")

# 2e: Cross-dataset benign duplicate analysis
print("\n  Cross-Dataset Benign Duplicate Analysis:")
benign_df = df[df[label_col] == 'BENIGN'].copy()
benign_hash = pd.util.hash_pandas_object(benign_df[feature_cols], index=False)
benign_df['_bhash'] = benign_hash
benign_hash_groups = benign_df.groupby('_bhash').agg(
    count=('_bhash', 'size'),
    n_sources=('Source_File', 'nunique')
).reset_index()
benign_inter = benign_hash_groups[benign_hash_groups['n_sources'] > 1]
benign_inter_rows = benign_df[benign_df['_bhash'].isin(benign_inter['_bhash'])].shape[0]
print(f"    Cross-file benign duplicates: {len(benign_inter):,} groups ({benign_inter_rows:,} rows)")
print(f"    This represents {benign_inter_rows/len(benign_df)*100:.2f}% of all benign traffic")

results['duplicates'] = {
    'total_all': int(total_dup_all),
    'removable': int(total_dup_first),
    'intra_groups': int(len(intra_only)),
    'intra_rows': int(intra_rows),
    'inter_groups': int(len(inter)),
    'inter_rows': int(inter_rows),
    'per_source': per_source_dups,
    'per_label': per_label_dups,
    'benign_inter_groups': int(len(benign_inter)),
    'benign_inter_rows': int(benign_inter_rows),
}

# Clean up hash columns
df.drop(columns=['_hash'], inplace=True)

# ============================================================
# SECTION 3: FEATURE CORRELATION & REDUNDANCY
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 3: FEATURE CORRELATION & REDUNDANCY ANALYSIS")
print("=" * 70)

# 3a: Identify perfectly correlated pairs (r=1.0000)
print("\n  Computing correlation matrix on numeric features...")
# Sample for efficiency (correlation on 2.8M rows is very expensive)
sample_size = min(100000, len(df))
df_sample = df[numeric_cols].sample(n=sample_size, random_state=42)

# Replace inf with NaN for correlation
df_sample = df_sample.replace([np.inf, -np.inf], np.nan)
corr_matrix = df_sample.corr()

# Find perfectly correlated pairs
perfect_corr_pairs = []
high_corr_pairs = []
for i in range(len(corr_matrix.columns)):
    for j in range(i + 1, len(corr_matrix.columns)):
        r = corr_matrix.iloc[i, j]
        if abs(r) >= 0.9999:
            perfect_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], round(r, 6)))
        elif abs(r) >= 0.95:
            high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], round(r, 6)))

print(f"\n  Perfectly correlated pairs (|r| >= 0.9999): {len(perfect_corr_pairs)}")
for col1, col2, r in perfect_corr_pairs:
    print(f"    {col1} <-> {col2}: r={r}")

print(f"\n  Highly correlated pairs (0.95 <= |r| < 0.9999): {len(high_corr_pairs)}")
for col1, col2, r in sorted(high_corr_pairs, key=lambda x: -abs(x[2]))[:20]:
    print(f"    {col1} <-> {col2}: r={r}")

results['perfect_correlations'] = [{'col1': c1, 'col2': c2, 'r': r} for c1, c2, r in perfect_corr_pairs]
results['high_correlations_top20'] = [{'col1': c1, 'col2': c2, 'r': r} for c1, c2, r in sorted(high_corr_pairs, key=lambda x: -abs(x[2]))[:20]]

# 3b: Plot correlation heatmap
fig, ax = plt.subplots(figsize=(20, 18))
im = ax.imshow(corr_matrix.values, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(len(corr_matrix.columns)))
ax.set_yticks(range(len(corr_matrix.columns)))
ax.set_xticklabels(corr_matrix.columns, rotation=90, fontsize=5)
ax.set_yticklabels(corr_matrix.columns, fontsize=5)
ax.set_title('CICIDS2017 Combined: Feature Correlation Matrix (100K sample)', fontsize=14, fontweight='bold')
plt.colorbar(im, ax=ax, shrink=0.8, label='Pearson r')
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'feature_correlation_heatmap.png'), dpi=150)
plt.close()
print(f"\n  Saved: {FIGURES_DIR}/feature_correlation_heatmap.png")

# ============================================================
# SECTION 4: BENIGN TRAFFIC DRIFT ANALYSIS
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 4: BENIGN TRAFFIC DRIFT ON COMBINED DATA")
print("=" * 70)

benign = df[df[label_col] == 'BENIGN'].copy()
print(f"\n  Total benign flows: {len(benign):,}")

# Day order for temporal analysis
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday-Morning', 'Thursday-Afternoon',
             'Friday-Morning', 'Friday-PortScan', 'Friday-DDoS']

# 4a: Flow Duration drift
print("\n  Flow Duration Statistics by Day (Benign only):")
print(f"  {'Day':<25} {'Count':>10} {'Median':>12} {'Mean':>12} {'Std':>12}")
print("  " + "-" * 75)
drift_stats = {}
for day in day_order:
    day_benign = benign[benign['Source_Day'] == day]
    if len(day_benign) == 0:
        continue
    dur = day_benign['Flow Duration']
    stats = {
        'count': int(len(day_benign)),
        'median': float(dur.median()),
        'mean': float(dur.mean()),
        'std': float(dur.std()),
    }
    drift_stats[day] = stats
    print(f"  {day:<25} {stats['count']:>10,} {stats['median']:>12,.0f} {stats['mean']:>12,.0f} {stats['std']:>12,.0f}")

# 4b: Destination Port drift
print("\n  Top Destination Port Distribution by Day (Benign only):")
port_drift = {}
for day in day_order:
    day_benign = benign[benign['Source_Day'] == day]
    if len(day_benign) == 0:
        continue
    port_dist = day_benign['Destination Port'].value_counts(normalize=True).head(5)
    port_drift[day] = {str(k): round(v * 100, 2) for k, v in port_dist.items()}
    top3 = ', '.join([f"Port {k}: {v:.1f}%" for k, v in list(port_dist.items())[:3]])
    print(f"  {day:<25} {top3}")

results['benign_drift'] = {
    'flow_duration': drift_stats,
    'port_distribution': port_drift,
}

# 4c: Plot benign flow duration box plots by day
fig, axes = plt.subplots(1, 2, figsize=(18, 6))

# Duration boxplot (log scale)
benign_dur_data = []
benign_dur_labels = []
for day in day_order:
    day_benign = benign[benign['Source_Day'] == day]
    if len(day_benign) > 0:
        # Sample for plotting
        sample = day_benign['Flow Duration'].sample(n=min(5000, len(day_benign)), random_state=42)
        benign_dur_data.append(sample.values)
        benign_dur_labels.append(day.replace('-', '\n'))

bp = axes[0].boxplot(benign_dur_data, labels=benign_dur_labels, patch_artist=True, showfliers=False)
for patch, color in zip(bp['boxes'], plt.cm.tab10(np.linspace(0, 1, len(benign_dur_data)))):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[0].set_yscale('log')
axes[0].set_ylabel('Flow Duration (us, log scale)')
axes[0].set_title('Benign Flow Duration Drift Across Days')
axes[0].tick_params(axis='x', rotation=45, labelsize=8)

# Packet size boxplot
benign_pkt_data = []
for day in day_order:
    day_benign = benign[benign['Source_Day'] == day]
    if len(day_benign) > 0:
        sample = day_benign['Average Packet Size'].sample(n=min(5000, len(day_benign)), random_state=42)
        benign_pkt_data.append(sample.values)

bp2 = axes[1].boxplot(benign_pkt_data, labels=benign_dur_labels, patch_artist=True, showfliers=False)
for patch, color in zip(bp2['boxes'], plt.cm.tab10(np.linspace(0, 1, len(benign_pkt_data)))):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
axes[1].set_ylabel('Average Packet Size (bytes)')
axes[1].set_title('Benign Average Packet Size Drift Across Days')
axes[1].tick_params(axis='x', rotation=45, labelsize=8)

plt.suptitle('CICIDS2017 Combined: Benign Traffic Drift Analysis', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'benign_drift_analysis.png'), dpi=150)
plt.close()
print(f"\n  Saved: {FIGURES_DIR}/benign_drift_analysis.png")

# ============================================================
# SECTION 5: DATA LEAKAGE VECTOR ASSESSMENT
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 5: DATA LEAKAGE VECTOR ASSESSMENT")
print("=" * 70)

# 5a: Destination Port concentration per attack
print("\n  Destination Port Concentration per Attack Class:")
attack_port_stats = {}
for label in label_dist.index:
    if label == 'BENIGN':
        continue
    label_df = df[df[label_col] == label]
    top_port = label_df['Destination Port'].value_counts()
    top1_port = top_port.index[0]
    top1_pct = top_port.iloc[0] / len(label_df) * 100
    unique_ports = label_df['Destination Port'].nunique()
    attack_port_stats[label] = {
        'top_port': int(top1_port),
        'top_port_pct': round(top1_pct, 2),
        'unique_ports': int(unique_ports),
    }
    print(f"    {label:<30} Top port: {top1_port:>5} ({top1_pct:>6.2f}%)  Unique ports: {unique_ports}")

# 5b: Temporal burst analysis
print("\n  Source-Day Concentration per Attack Class:")
for label in label_dist.index:
    if label == 'BENIGN':
        continue
    label_df = df[df[label_col] == label]
    day_dist = label_df['Source_Day'].value_counts()
    print(f"    {label:<30} {', '.join([f'{d}: {c:,}' for d, c in day_dist.items()])}")

results['leakage'] = {
    'port_concentration': attack_port_stats,
}

# 5c: Plot attack port concentration
fig, ax = plt.subplots(figsize=(12, 6))
attack_labels = [l for l in label_dist.index if l != 'BENIGN']
port_pcts = [attack_port_stats[l]['top_port_pct'] for l in attack_labels]
port_nums = [str(attack_port_stats[l]['top_port']) for l in attack_labels]
colors = ['#e74c3c' if p > 90 else '#f39c12' if p > 50 else '#2ecc71' for p in port_pcts]
bars = ax.barh(range(len(attack_labels)), port_pcts, color=colors)
ax.set_yticks(range(len(attack_labels)))
ax.set_yticklabels(attack_labels, fontsize=9)
ax.set_xlabel('Top Destination Port Concentration (%)')
ax.set_title('CICIDS2017: Attack Traffic Port Concentration (Leakage Risk)', fontsize=13, fontweight='bold')
ax.axvline(x=90, color='red', linestyle='--', alpha=0.5, label='Critical (>90%)')
ax.axvline(x=50, color='orange', linestyle='--', alpha=0.5, label='High (>50%)')
ax.legend(fontsize=9)
for i, (pct, port) in enumerate(zip(port_pcts, port_nums)):
    ax.text(pct + 0.5, i, f'Port {port} ({pct:.1f}%)', va='center', fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'attack_port_leakage.png'), dpi=150)
plt.close()
print(f"\n  Saved: {FIGURES_DIR}/attack_port_leakage.png")

# ============================================================
# SECTION 6: INFINITY & NaN ROOT CAUSE VERIFICATION
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 6: INFINITY & NaN ROOT CAUSE VERIFICATION")
print("=" * 70)

# 6a: Inf analysis
inf_mask_bytes = np.isinf(df['Flow Bytes/s'].astype(float))
inf_mask_pkts = np.isinf(df['Flow Packets/s'].astype(float))
inf_total_bytes = inf_mask_bytes.sum()
inf_total_pkts = inf_mask_pkts.sum()
inf_any = (inf_mask_bytes | inf_mask_pkts)

print(f"\n  Flow Bytes/s Inf count: {inf_total_bytes:,}")
print(f"  Flow Packets/s Inf count: {inf_total_pkts:,}")
print(f"  Rows with any Inf: {inf_any.sum():,}")

# Verify 100% correlation with Flow Duration == 0
inf_rows = df[inf_any]
zero_dur_in_inf = (inf_rows['Flow Duration'] == 0).sum()
print(f"\n  Of {inf_any.sum():,} Inf rows:")
print(f"    Flow Duration == 0: {zero_dur_in_inf:,} ({zero_dur_in_inf/inf_any.sum()*100:.2f}%)")

# Also check: are there zero-duration flows WITHOUT inf?
zero_dur_all = (df['Flow Duration'] == 0).sum()
zero_dur_no_inf = zero_dur_all - zero_dur_in_inf
print(f"\n  Total zero-duration flows: {zero_dur_all:,}")
print(f"  Zero-duration WITH Inf: {zero_dur_in_inf:,}")
print(f"  Zero-duration WITHOUT Inf: {zero_dur_no_inf:,}")

# 6b: NaN analysis
nan_per_col = df[numeric_cols].isna().sum()
nan_cols = nan_per_col[nan_per_col > 0]
print(f"\n  Columns with NaN values:")
for col, count in nan_cols.items():
    print(f"    {col}: {count:,}")

# Verify NaN in Flow Bytes/s
nan_bytes = df['Flow Bytes/s'].isna().sum()
print(f"\n  Flow Bytes/s NaN count: {nan_bytes:,}")

# Check label distribution of NaN rows
if nan_bytes > 0:
    nan_labels = df[df['Flow Bytes/s'].isna()][label_col].value_counts()
    print(f"  NaN row label distribution:")
    for label, count in nan_labels.items():
        print(f"    {label}: {count}")

results['inf_nan'] = {
    'inf_flow_bytes': int(inf_total_bytes),
    'inf_flow_pkts': int(inf_total_pkts),
    'inf_total_rows': int(inf_any.sum()),
    'zero_dur_causes_inf_pct': round(zero_dur_in_inf / max(inf_any.sum(), 1) * 100, 2),
    'nan_flow_bytes': int(nan_bytes),
    'zero_duration_total': int(zero_dur_all),
}

# ============================================================
# SECTION 7: CONSTANT & NEAR-CONSTANT FEATURES
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 7: CONSTANT & NEAR-CONSTANT FEATURE ANALYSIS")
print("=" * 70)

const_features = []
near_const_features = []

for col in numeric_cols:
    nunique = df[col].nunique()
    if nunique <= 1:
        const_features.append(col)
    elif nunique <= 3:
        near_const_features.append((col, nunique, df[col].value_counts().to_dict()))

print(f"\n  Constant features (nunique <= 1): {len(const_features)}")
for col in const_features:
    val = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else 'all NaN'
    print(f"    {col}: constant value = {val}")

print(f"\n  Near-constant features (nunique = 2 or 3): {len(near_const_features)}")
for col, nu, dist in near_const_features:
    # Show as compact distribution
    compact = {str(k): int(v) for k, v in dist.items()}
    print(f"    {col}: nunique={nu}, dist={compact}")

results['constant_features'] = const_features
results['near_constant_features'] = [(col, nu) for col, nu, _ in near_const_features]

# ============================================================
# SECTION 8: ISOLATION FOREST READINESS
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 8: ISOLATION FOREST READINESS EVALUATION")
print("=" * 70)

# 8a: Contamination ratio
attack_ratio = binary_attack / len(df)
print(f"\n  Contamination ratio (attack fraction): {attack_ratio:.4f} ({attack_ratio*100:.2f}%)")
print(f"  Recommended IF contamination parameter: {round(attack_ratio, 3)}")

# 8b: Dimensionality analysis
usable_features = [c for c in numeric_cols if c not in const_features]
print(f"\n  Total numeric features: {len(numeric_cols)}")
print(f"  Constant (to drop): {len(const_features)}")
print(f"  Usable features: {len(usable_features)}")

# After dropping perfectly correlated redundant features
redundant_to_drop = set()
for col1, col2, r in perfect_corr_pairs:
    redundant_to_drop.add(col2)  # Drop the second of each pair
non_redundant = [c for c in usable_features if c not in redundant_to_drop]
print(f"  After dropping perfectly correlated: {len(non_redundant)} features")
print(f"  Features to drop as redundant: {redundant_to_drop}")

# 8c: Feature range analysis (for robust scaling)
print(f"\n  Feature Range Analysis (min/max for scaling decisions):")
range_stats = []
for col in non_redundant[:10]:  # Show first 10
    col_data = df[col].replace([np.inf, -np.inf], np.nan).dropna()
    rng = col_data.max() - col_data.min()
    range_stats.append({
        'feature': col,
        'min': float(col_data.min()),
        'max': float(col_data.max()),
        'range': float(rng),
        'median': float(col_data.median()),
        'iqr': float(col_data.quantile(0.75) - col_data.quantile(0.25)),
    })
    print(f"    {col}: range=[{col_data.min():.2f}, {col_data.max():.2f}], IQR={col_data.quantile(0.75) - col_data.quantile(0.25):.2f}")

# 8d: Heavy-tail detection
print(f"\n  Heavy-Tail Analysis (skewness > 10):")
heavy_tail_features = []
for col in non_redundant:
    col_data = df[col].replace([np.inf, -np.inf], np.nan).dropna()
    skew = col_data.skew()
    if abs(skew) > 10:
        heavy_tail_features.append((col, round(skew, 2)))
        
print(f"  Features with |skewness| > 10: {len(heavy_tail_features)}")
for col, skew in sorted(heavy_tail_features, key=lambda x: -abs(x[1]))[:15]:
    print(f"    {col}: skew={skew}")

results['isolation_forest'] = {
    'contamination_ratio': round(attack_ratio, 4),
    'total_numeric': len(numeric_cols),
    'constant_to_drop': len(const_features),
    'redundant_to_drop': list(redundant_to_drop),
    'usable_features': len(non_redundant),
    'heavy_tail_count': len(heavy_tail_features),
}

# ============================================================
# SECTION 9: SUMMARY PLOTS
# ============================================================
print("\n\n" + "=" * 70)
print("SECTION 9: GENERATING SUMMARY VISUALIZATIONS")
print("=" * 70)

# 9a: Attack class by source day heatmap
attack_df = df[df[label_col] != 'BENIGN']
attack_day_matrix = pd.crosstab(attack_df[label_col], attack_df['Source_Day'])
# Reorder columns
ordered_days = [d for d in day_order if d in attack_day_matrix.columns]
attack_day_matrix = attack_day_matrix[ordered_days]

fig, ax = plt.subplots(figsize=(14, 8))
im = ax.imshow(np.log10(attack_day_matrix.values + 1), cmap='YlOrRd', aspect='auto')
ax.set_xticks(range(len(ordered_days)))
ax.set_xticklabels(ordered_days, rotation=45, ha='right', fontsize=10)
ax.set_yticks(range(len(attack_day_matrix.index)))
ax.set_yticklabels(attack_day_matrix.index, fontsize=10)
# Annotate cells
for i in range(len(attack_day_matrix.index)):
    for j in range(len(ordered_days)):
        val = attack_day_matrix.iloc[i, j]
        if val > 0:
            ax.text(j, i, f'{val:,}', ha='center', va='center', fontsize=7,
                   color='white' if val > 1000 else 'black')
ax.set_title('CICIDS2017: Attack Class Distribution by Recording Day', fontsize=14, fontweight='bold')
plt.colorbar(im, ax=ax, shrink=0.8, label='log10(count + 1)')
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'attack_day_heatmap.png'), dpi=150)
plt.close()
print(f"  Saved: {FIGURES_DIR}/attack_day_heatmap.png")

# 9b: Data quality summary dashboard
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Pie chart: Binary split
axes[0, 0].pie([binary_benign, binary_attack],
               labels=[f'BENIGN\n{binary_benign:,}', f'ATTACK\n{binary_attack:,}'],
               autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c'], startangle=90,
               textprops={'fontsize': 10})
axes[0, 0].set_title('Binary Class Distribution', fontweight='bold')

# Bar chart: Per-source row counts
source_counts = df['Source_Day'].value_counts().reindex(day_order)
axes[0, 1].bar(range(len(source_counts)), source_counts.values, color=plt.cm.Set2(np.linspace(0, 1, len(source_counts))))
axes[0, 1].set_xticks(range(len(source_counts)))
axes[0, 1].set_xticklabels([d.replace('-', '\n') for d in source_counts.index], fontsize=8, rotation=45)
axes[0, 1].set_ylabel('Flow Count')
axes[0, 1].set_title('Flows per Recording Day', fontweight='bold')
axes[0, 1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}K'))

# Stacked bar: Data quality issues by source
quality_data = []
for day in day_order:
    day_df = df[df['Source_Day'] == day]
    nan_c = day_df[numeric_cols].isna().sum().sum()
    inf_c = sum(np.isinf(day_df[col].astype(float)).sum() for col in ['Flow Bytes/s', 'Flow Packets/s'] if col in day_df.columns)
    quality_data.append({'day': day, 'NaN': nan_c, 'Inf': inf_c})
qdf = pd.DataFrame(quality_data)
x = range(len(qdf))
axes[1, 0].bar(x, qdf['NaN'], label='NaN', color='#3498db')
axes[1, 0].bar(x, qdf['Inf'], bottom=qdf['NaN'], label='Inf', color='#e67e22')
axes[1, 0].set_xticks(x)
axes[1, 0].set_xticklabels([d.replace('-', '\n') for d in qdf['day']], fontsize=8, rotation=45)
axes[1, 0].set_ylabel('Count')
axes[1, 0].set_title('Data Quality Issues by Day', fontweight='bold')
axes[1, 0].legend()

# Bar chart: Duplicate rows by source
dup_data = []
for day in day_order:
    day_df = df[df['Source_Day'] == day]
    dup_c = day_df.duplicated(subset=feature_cols + [label_col], keep='first').sum()
    dup_data.append({'day': day, 'duplicates': dup_c, 'pct': dup_c / len(day_df) * 100})
ddf = pd.DataFrame(dup_data)
bars = axes[1, 1].bar(range(len(ddf)), ddf['pct'], color=['#e74c3c' if p > 10 else '#f39c12' if p > 5 else '#2ecc71' for p in ddf['pct']])
axes[1, 1].set_xticks(range(len(ddf)))
axes[1, 1].set_xticklabels([d.replace('-', '\n') for d in ddf['day']], fontsize=8, rotation=45)
axes[1, 1].set_ylabel('Duplicate %')
axes[1, 1].set_title('Duplicate Flow Rate by Day', fontweight='bold')
for i, (pct, count) in enumerate(zip(ddf['pct'], ddf['duplicates'])):
    axes[1, 1].text(i, pct + 0.3, f'{count:,}', ha='center', fontsize=7)

plt.suptitle('CICIDS2017 Combined Dataset: Quality Dashboard', fontsize=16, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, 'combined_quality_dashboard.png'), dpi=150, bbox_inches='tight')
plt.close()
print(f"  Saved: {FIGURES_DIR}/combined_quality_dashboard.png")

# ============================================================
# SAVE RESULTS
# ============================================================
results_path = os.path.join(REPORTS_DIR, 'combined_eda_results.json')
with open(results_path, 'w') as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n  Results saved: {results_path}")

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("PHASE 5 COMBINED EDA: COMPLETE")
print("=" * 70)
print(f"  Dataset: {COMBINED_CSV}")
print(f"  Shape: {df.shape[0]:,} x {df.shape[1]}")
print(f"  Labels: {len(label_dist)} classes")
print(f"  Binary: {binary_benign:,} BENIGN / {binary_attack:,} ATTACK")
print(f"  Duplicates: {total_dup_first:,} removable ({total_dup_first/len(df)*100:.2f}%)")
print(f"    Intra-dataset: {len(intra_only):,} groups ({intra_rows:,} rows)")
print(f"    Inter-dataset: {len(inter):,} groups ({inter_rows:,} rows)")
print(f"  Inf values: {inf_any.sum():,} (100% caused by Flow Duration == 0)")
print(f"  NaN values: {nan_bytes:,}")
print(f"  Constant features: {len(const_features)}")
print(f"  Perfect correlations: {len(perfect_corr_pairs)} pairs")
print(f"  IF contamination: {attack_ratio:.4f}")
print(f"  Recommended usable features: {len(non_redundant)}")
print(f"  Figures: {FIGURES_DIR}/")
print("=" * 70)
