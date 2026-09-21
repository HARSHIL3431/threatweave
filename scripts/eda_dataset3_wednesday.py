import os
import sys
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 150

fig_dir = "figures/wednesday"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Wednesday-workingHours.pcap_ISCX.csv"
print(f"Loading {csv_path}...")

df = pd.read_csv(csv_path, encoding='latin1', low_memory=False)
raw_shape = df.shape
print(f"Raw shape: {raw_shape}")

# Clean column names
df.columns = [c.strip() for c in df.columns]

# Resolve duplicate column 'Fwd Header Length'
cols = list(df.columns)
if cols.count('Fwd Header Length') > 1:
    first_idx = cols.index('Fwd Header Length')
    second_idx = cols.index('Fwd Header Length', first_idx + 1)
    cols[second_idx] = 'Fwd Header Length.1'
    df.columns = cols

total_rows = len(df)
label_col = 'Label'

# 1. Structure & Quality
dup_rows = int(df.duplicated().sum())
dup_pct = round((dup_rows / total_rows) * 100, 2)

# Convert numeric columns
num_cols = [c for c in df.columns if c != label_col]
inf_counts = {}
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')
    inf_cnt = int(np.isinf(df[c]).sum())
    if inf_cnt > 0:
        inf_counts[c] = inf_cnt

nan_counts = df.isna().sum()
cols_with_nan = {k: int(v) for k, v in nan_counts[nan_counts > 0].items()}

print(f"\n--- Baseline Quality (Wednesday) ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Labels & Imbalance
label_counts = df[label_col].value_counts()
print(f"\n--- Label Breakdown ---")
for k, v in label_counts.items():
    print(f"  - {k}: {v:,} ({round(v/total_rows*100, 4)}%)")

# 3. Inf Analysis & Attack association
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
inf_df = df[inf_mask]
print(f"\nInf values by Label: {inf_df[label_col].value_counts().to_dict()}")
inf_zero_dur = int((inf_df['Flow Duration'] == 0).sum())
print(f"Inf records with Flow Duration == 0: {inf_zero_dur} / {len(inf_df)} ({round(inf_zero_dur/len(inf_df)*100, 2)}%)")

# 4. Cybersecurity Investigation: DoS Attacks & Heartbleed
print(f"\n--- Cybersecurity Investigation: DoS Family & Heartbleed ---")

# Heartbleed deep dive (11 flows)
hb_df = df[df[label_col] == 'Heartbleed']
print("\nHeartbleed Profile (11 records):")
print(f"Destination Ports: {hb_df['Destination Port'].value_counts().to_dict()}")
print(f"Flow Duration (ms) mean: {hb_df['Flow Duration'].mean() / 1000:.2f}, median: {hb_df['Flow Duration'].median() / 1000:.2f}")
print(f"Total Fwd Packets mean: {hb_df['Total Fwd Packets'].mean():.2f}, Total Bwd Packets mean: {hb_df['Total Backward Packets'].mean():.2f}")
print(f"Total Length of Bwd Packets mean: {hb_df['Total Length of Bwd Packets'].mean():.2f}")

# Compare Volumetric DoS (Hulk, GoldenEye) vs Slow DoS (slowloris, Slowhttptest) vs Benign
behavior_metrics = [
    'Flow Duration', 'Flow Packets/s', 'Flow Bytes/s', 'Flow IAT Mean', 'Flow IAT Max',
    'Total Fwd Packets', 'Total Backward Packets', 'Fwd Packet Length Mean', 'Bwd Packet Length Mean'
]

comp_rows = []
for l in label_counts.index:
    sub = df[df[label_col] == l].replace([np.inf, -np.inf], np.nan)
    r = {"Class": l, "Count": len(sub)}
    for m in behavior_metrics:
        r[f"{m}_mean"] = round(float(sub[m].mean()), 2)
        r[f"{m}_median"] = round(float(sub[m].median()), 2)
    comp_rows.append(r)

comp_df = pd.DataFrame(comp_rows)
print("\nDoS Family Flow Dynamics Comparison (Medians):")
print(comp_df[['Class', 'Flow Duration_median', 'Flow Packets/s_median', 'Flow IAT Mean_median', 'Total Fwd Packets_median', 'Total Backward Packets_median']])

# Destination Port Analysis for Wednesday Attacks
ports_by_class = df.groupby(label_col)['Destination Port'].value_counts()
print("\nDestination Port distribution for each attack:")
for l in label_counts.index:
    if l != 'BENIGN':
        print(f"[{l}] Ports:\n{ports_by_class.get(l, pd.Series()).head(3)}")

# 5. Generate Figures
# Figure 1: Label Distribution Log Scale
plt.figure(figsize=(10, 5))
ax = sns.barplot(x=label_counts.index, y=label_counts.values, palette='tab10')
plt.title("Wednesday: Class Distribution (DoS Family & Heartbleed)", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count (log scale)", fontsize=11)
plt.yscale('log')
plt.xticks(rotation=15, ha='right')
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=8, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/wednesday_label_distribution.png")
plt.close()

# Figure 2: Volumetric DoS vs Slow DoS Flow Duration
plt.figure(figsize=(11, 5.5))
df['log_Flow_Duration'] = np.log10(df['Flow Duration'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_Duration', palette='tab10')
plt.title("Wednesday: Flow Duration across Benign and DoS Attack Types", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Attack Class", fontsize=11)
plt.ylabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.xticks(rotation=15, ha='right')
plt.tight_layout()
plt.savefig(f"{fig_dir}/wednesday_flow_duration_dos_comparison.png")
plt.close()

# Figure 3: Flow Inter-Arrival Time (Flow IAT Mean)
plt.figure(figsize=(11, 5.5))
df['log_Flow_IAT_Mean'] = np.log10(df['Flow IAT Mean'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_IAT_Mean', palette='tab10')
plt.title("Wednesday: Flow Inter-Arrival Time Mean (log10 µs) by Class", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Attack Class", fontsize=11)
plt.ylabel("log10(Flow IAT Mean + 1 µs)", fontsize=11)
plt.xticks(rotation=15, ha='right')
plt.tight_layout()
plt.savefig(f"{fig_dir}/wednesday_flow_iat_mean_comparison.png")
plt.close()

# Figure 4: Heartbleed Flow Feature Inspection (Scatter/Bar)
plt.figure(figsize=(9, 5))
hb_features = pd.DataFrame({
    'Metric': ['Fwd Packets', 'Bwd Packets', 'Fwd Length (kB)', 'Bwd Length (kB)'],
    'Mean Value': [
        hb_df['Total Fwd Packets'].mean(),
        hb_df['Total Backward Packets'].mean(),
        hb_df['Total Length of Fwd Packets'].mean() / 1024,
        hb_df['Total Length of Bwd Packets'].mean() / 1024
    ]
})
sns.barplot(data=hb_features, x='Metric', y='Mean Value', color='#d62728')
plt.title("Heartbleed Attack Profile (11 Flows): Average Packets & Volume", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Average Value", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/wednesday_heartbleed_profile.png")
plt.close()

# Save JSON results
wednesday_results = {
    "dataset": "Wednesday-workingHours.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels": {k: int(v) for k, v in label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "inf_zero_dur": inf_zero_dur,
    "heartbleed_count": len(hb_df),
    "heartbleed_ports": hb_df['Destination Port'].value_counts().to_dict(),
    "hulk_count": int(label_counts.get('DoS Hulk', 0)),
    "goldeneye_count": int(label_counts.get('DoS GoldenEye', 0)),
    "slowloris_count": int(label_counts.get('DoS slowloris', 0)),
    "slowhttptest_count": int(label_counts.get('DoS Slowhttptest', 0))
}
with open("reports/wednesday_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(wednesday_results, f, indent=2)

print("\nWednesday analysis completed successfully.")
