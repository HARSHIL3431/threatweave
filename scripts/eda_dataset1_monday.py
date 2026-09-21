import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Set plotting style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 150

fig_dir = "figures/monday"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Monday-WorkingHours.pcap_ISCX.csv"
print(f"Loading {csv_path}...")

# Load dataset
df = pd.read_csv(csv_path, encoding='latin1', low_memory=False)
raw_shape = df.shape
print(f"Raw shape: {raw_shape}")

# Clean column names (strip whitespace)
df.columns = [c.strip() for c in df.columns]

# Resolve duplicate column 'Fwd Header Length' by appending .1 to second occurrence
cols = list(df.columns)
if cols.count('Fwd Header Length') > 1:
    first_idx = cols.index('Fwd Header Length')
    second_idx = cols.index('Fwd Header Length', first_idx + 1)
    cols[second_idx] = 'Fwd Header Length.1'
    df.columns = cols

print(f"Cleaned columns count: {len(df.columns)}")

# 1. Structure & Quality
label_col = 'Label'
total_rows = len(df)
dup_rows = int(df.duplicated().sum())
dup_pct = round((dup_rows / total_rows) * 100, 2)

# Check NaNs and Infs
nan_counts = df.isna().sum()
cols_with_nan = nan_counts[nan_counts > 0].to_dict()

# Numerical conversion for inspection
num_cols = [c for c in df.columns if c != label_col]
inf_counts = {}
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')
    inf_cnt = int(np.isinf(df[c]).sum())
    if inf_cnt > 0:
        inf_counts[c] = inf_cnt

print(f"\n--- Baseline Quality ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Infinite Values Root Cause Analysis
# Check if Flow Duration == 0 explains Infs in Flow Bytes/s and Flow Packets/s
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
inf_rows = df[inf_mask]
inf_zero_duration = int((inf_rows['Flow Duration'] == 0).sum())
print(f"\n--- Inf Root Cause Analysis ---")
print(f"Total Inf records: {len(inf_rows):,}")
print(f"Inf records with Flow Duration == 0: {inf_zero_duration:,} ({round(inf_zero_duration/len(inf_rows)*100, 2)}%)")
print(f"Inf records packet count distribution:")
print(inf_rows['Total Fwd Packets'].value_counts().head(5))

# 3. Label Breakdown
labels = df[label_col].value_counts()
print(f"\n--- Label Distribution ---")
print(labels)

# 4. Numerical Summary Statistics
stats_list = []
for c in num_cols:
    s = df[c].replace([np.inf, -np.inf], np.nan)
    stats_list.append({
        "Feature": c,
        "Mean": float(s.mean()),
        "Median": float(s.median()),
        "Std": float(s.std()),
        "Min": float(s.min()),
        "Q25": float(s.quantile(0.25)),
        "Q75": float(s.quantile(0.75)),
        "Max": float(s.max()),
        "Skewness": float(s.skew()),
        "Zero_Pct": round(float((s == 0).mean()) * 100, 2),
        "Unique_Count": int(s.nunique())
    })
stats_df = pd.DataFrame(stats_list)

# Identify constant and near zero variance features
constant_features = stats_df[stats_df['Unique_Count'] <= 1]['Feature'].tolist()
near_zero_var = stats_df[(stats_df['Unique_Count'] > 1) & (stats_df['Std'] < 1e-4)]['Feature'].tolist()
highly_skewed = stats_df[stats_df['Skewness'].abs() > 20]['Feature'].tolist()

print(f"\nConstant Features ({len(constant_features)}): {constant_features}")
print(f"Near Zero Variance Features ({len(near_zero_var)}): {near_zero_var}")
print(f"Highly Skewed Features (|skew| > 20) ({len(highly_skewed)}): {len(highly_skewed)}")

# 5. Cybersecurity & Network Behavioral Profiling (Monday Benign)
# Destination Port Analysis
port_counts = df['Destination Port'].value_counts()
top_ports = port_counts.head(10)
port_names = {
    80: "HTTP (80)",
    443: "HTTPS (443)",
    53: "DNS (53)",
    22: "SSH (22)",
    21: "FTP (21)",
    25: "SMTP (25)",
    123: "NTP (123)",
    445: "SMB (445)",
    8080: "HTTP-Proxy (8080)",
    88: "Kerberos (88)",
    389: "LDAP (389)",
    137: "NetBIOS (137)",
    139: "NetBIOS (139)"
}
top_port_labeled = {f"{p} ({port_names.get(p, 'Other/Dynamic')})": cnt for p, cnt in top_ports.items()}
print(f"\n--- Top Destination Ports (Benign Baseline) ---")
for k, v in top_port_labeled.items():
    print(f"  {k}: {v:,} ({round(v/total_rows*100, 2)}%)")

# Flow Duration Analysis
dur_s = df['Flow Duration'].replace([np.inf, -np.inf], np.nan)
zero_dur_cnt = int((dur_s == 0).sum())
print(f"\nFlow Duration: Zero duration flows = {zero_dur_cnt:,} ({round(zero_dur_cnt/total_rows*100, 2)}%)")
print(f"Flow Duration quantiles (microseconds):")
print(dur_s.quantile([0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]))

# Forward vs Backward Packet Asymmetry
fwd_pkts = df['Total Fwd Packets']
bwd_pkts = df['Total Backward Packets']
fwd_only_flows = int(((fwd_pkts > 0) & (bwd_pkts == 0)).sum())
bwd_only_flows = int(((fwd_pkts == 0) & (bwd_pkts > 0)).sum())
bidirectional_flows = int(((fwd_pkts > 0) & (bwd_pkts > 0)).sum())
print(f"\n--- Flow Directionality ---")
print(f"Bidirectional Flows: {bidirectional_flows:,} ({round(bidirectional_flows/total_rows*100, 2)}%)")
print(f"Forward-Only Flows (No response): {fwd_only_flows:,} ({round(fwd_only_flows/total_rows*100, 2)}%)")
print(f"Backward-Only Flows: {bwd_only_flows:,} ({round(bwd_only_flows/total_rows*100, 2)}%)")

# Correlation & Redundancy Analysis (|r| >= 0.90)
valid_num_df = df[num_cols].replace([np.inf, -np.inf], np.nan).dropna()
corr_matrix = valid_num_df.corr().abs()
upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
high_corr_pairs = []
for col in upper_tri.columns:
    high_corr_idx = upper_tri.index[upper_tri[col] >= 0.90].tolist()
    for row in high_corr_idx:
        high_corr_pairs.append({
            "Feature_1": row,
            "Feature_2": col,
            "Pearson_r": round(float(upper_tri.loc[row, col]), 4)
        })
high_corr_df = pd.DataFrame(high_corr_pairs).sort_values(by="Pearson_r", ascending=False)
print(f"\nHighly Correlated Feature Pairs (|r| >= 0.90): {len(high_corr_pairs)}")
print(high_corr_df.head(10))

# 6. Generate Figures
# Figure 1: Top Destination Ports
plt.figure(figsize=(10, 5))
ports_plot_data = pd.DataFrame({
    'Port': [f"{p}\n{port_names.get(p, '')}" for p in top_ports.index],
    'Count': top_ports.values
})
ax = sns.barplot(data=ports_plot_data, x='Port', y='Count', color='#2b5c8f')
plt.title("Monday Benign: Top 10 Destination Ports Distribution", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Destination Port (Service)", fontsize=11)
plt.ylabel("Flow Count", fontsize=11)
plt.xticks(rotation=0)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=8, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/monday_top_destination_ports.png")
plt.close()

# Figure 2: Flow Duration Log Distribution
plt.figure(figsize=(10, 5))
log_dur = np.log10(df['Flow Duration'].clip(lower=1))
sns.histplot(log_dur, bins=50, kde=True, color='#1f77b4')
plt.title("Monday Benign: Flow Duration Distribution (log10 microseconds)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.ylabel("Frequency", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/monday_flow_duration_log_dist.png")
plt.close()

# Figure 3: Packet Length Mean vs Flow Bytes/s (sample 10k)
sample_df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['Packet Length Mean', 'Flow Bytes/s']).sample(n=min(10000, len(df)), random_state=42)
plt.figure(figsize=(9, 6))
plt.scatter(sample_df['Packet Length Mean'], np.log10(sample_df['Flow Bytes/s'] + 1), alpha=0.3, s=15, color='#2ca02c')
plt.title("Monday Benign: Packet Length Mean vs log10(Flow Bytes/s)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Packet Length Mean (bytes)", fontsize=11)
plt.ylabel("log10(Flow Bytes/s + 1)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/monday_packet_length_vs_byte_rate.png")
plt.close()

# Figure 4: Correlation Heatmap of Selected Flow Characteristics
key_features = [
    'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Flow Bytes/s', 'Flow Packets/s', 'Flow IAT Mean', 'Flow IAT Max',
    'Packet Length Mean', 'Packet Length Std', 'Average Packet Size',
    'Subflow Fwd Packets', 'Subflow Fwd Bytes'
]
plt.figure(figsize=(11, 9))
sns.heatmap(valid_num_df[key_features].corr(), annot=True, fmt=".2f", cmap="vlag", vmin=-1, vmax=1, square=True)
plt.title("Monday Benign: Correlation Matrix of Key Flow Features", fontsize=13, fontweight='bold', pad=12)
plt.tight_layout()
plt.savefig(f"{fig_dir}/monday_key_features_correlation.png")
plt.close()

# Save JSON results for report generation
monday_results = {
    "dataset": "Monday-WorkingHours.pcap_ISCX.csv",
    "total_rows": total_rows,
    "total_cols": len(df.columns),
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "inf_zero_duration": inf_zero_duration,
    "constant_features": constant_features,
    "near_zero_var": near_zero_var,
    "top_ports": {str(k): int(v) for k, v in top_ports.items()},
    "bidirectional_pct": round(bidirectional_flows/total_rows*100, 2),
    "fwd_only_pct": round(fwd_only_flows/total_rows*100, 2),
    "zero_dur_cnt": zero_dur_cnt,
    "high_corr_count": len(high_corr_pairs),
    "high_corr_top": high_corr_pairs[:10]
}
with open("reports/monday_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(monday_results, f, indent=2)

print("\nMonday analysis executed and figures saved successfully.")
