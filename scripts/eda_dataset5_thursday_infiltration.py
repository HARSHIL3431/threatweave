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

fig_dir = "figures/thursday_infiltration"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv"
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

print(f"\n--- Baseline Quality (Thursday Infiltration) ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Labels
label_counts = df[label_col].value_counts()
print(f"\n--- Label Breakdown ---")
for k, v in label_counts.items():
    print(f"  - {k}: {v:,} ({round(v/total_rows*100, 4)}%)")

# 3. Investigation of the 2 anomaly features (Fwd URG Flags, CWE Flag Count)
print("\n--- Flag Activation Investigation (Fwd URG Flags & CWE Flag Count) ---")
fwd_urg_vals = df['Fwd URG Flags'].value_counts()
cwe_vals = df['CWE Flag Count'].value_counts()
print(f"Fwd URG Flags value counts:\n{fwd_urg_vals}")
print(f"CWE Flag Count value counts:\n{cwe_vals}")
urg_by_label = df.groupby(label_col)['Fwd URG Flags'].value_counts()
cwe_by_label = df.groupby(label_col)['CWE Flag Count'].value_counts()
print(f"Fwd URG Flags by label:\n{urg_by_label}")
print(f"CWE Flag Count by label:\n{cwe_by_label}")

# 4. Infiltration Attack Deep-Dive (36 instances)
infil_df = df[df[label_col] == 'Infiltration']
print(f"\n--- Infiltration Attack Profile ({len(infil_df)} records) ---")
print(f"Destination Ports:\n{infil_df['Destination Port'].value_counts()}")
print(f"Flow Duration (ms) mean: {infil_df['Flow Duration'].mean()/1000:.2f}, median: {infil_df['Flow Duration'].median()/1000:.2f}, min: {infil_df['Flow Duration'].min()/1000:.2f}, max: {infil_df['Flow Duration'].max()/1000:.2f}")
print(f"Total Fwd Packets mean: {infil_df['Total Fwd Packets'].mean():.2f}, median: {infil_df['Total Fwd Packets'].median():.2f}")
print(f"Total Backward Packets mean: {infil_df['Total Backward Packets'].mean():.2f}, median: {infil_df['Total Backward Packets'].median():.2f}")
print(f"Fwd Packet Length Mean: {infil_df['Fwd Packet Length Mean'].mean():.2f}, Bwd Packet Length Mean: {infil_df['Bwd Packet Length Mean'].mean():.2f}")

# Compare Benign vs Infiltration
benign_df = df[df[label_col] == 'BENIGN'].replace([np.inf, -np.inf], np.nan)
infil_clean = infil_df.replace([np.inf, -np.inf], np.nan)

# 5. Generate Figures
# Figure 1: Class Imbalance Illustration
plt.figure(figsize=(7, 4.5))
ax = sns.barplot(x=label_counts.index, y=label_counts.values, palette=['#2b5c8f', '#e41a1c'])
plt.title("Thursday Afternoon: Class Distribution (Severe Infiltration Imbalance)", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count (log scale)", fontsize=11)
plt.yscale('log')
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/thursday_infiltration_label_distribution.png")
plt.close()

# Figure 2: Destination Port Distribution for Infiltration
plt.figure(figsize=(8, 4.5))
infil_ports = infil_df['Destination Port'].value_counts()
ax = sns.barplot(x=[str(p) for p in infil_ports.index], y=infil_ports.values, color='#e41a1c')
plt.title("Thursday Afternoon: Destination Ports of Infiltration Traffic (36 Flows)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Destination Port", fontsize=11)
plt.ylabel("Flow Count", fontsize=11)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/thursday_infiltration_ports.png")
plt.close()

# Figure 3: Flow Duration Comparison (Boxplot log scale)
plt.figure(figsize=(8, 5))
df['log_Flow_Duration'] = np.log10(df['Flow Duration'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_Duration', palette=['#2b5c8f', '#e41a1c'])
plt.title("Thursday Afternoon: Flow Duration (Benign vs Infiltration)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class", fontsize=11)
plt.ylabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/thursday_infiltration_duration_comparison.png")
plt.close()

# Save JSON results
thursday_infil_results = {
    "dataset": "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels": {k: int(v) for k, v in label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "infil_ports": infil_ports.to_dict(),
    "fwd_urg_counts": fwd_urg_vals.to_dict(),
    "cwe_counts": cwe_vals.to_dict()
}
with open("reports/thursday_infiltration_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(thursday_infil_results, f, indent=2)

print("\nThursday Afternoon Infiltration analysis completed successfully.")
