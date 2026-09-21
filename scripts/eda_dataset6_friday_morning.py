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

fig_dir = "figures/friday_morning"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Friday-WorkingHours-Morning.pcap_ISCX.csv"
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

print(f"\n--- Baseline Quality (Friday Morning) ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Labels
label_counts = df[label_col].value_counts()
print(f"\n--- Label Breakdown ---")
for k, v in label_counts.items():
    print(f"  - {k}: {v:,} ({round(v/total_rows*100, 4)}%)")

# 3. Inf Root Cause
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
inf_df = df[inf_mask]
print(f"\nInf values by Label: {inf_df[label_col].value_counts().to_dict()}")
inf_zero_dur = int((inf_df['Flow Duration'] == 0).sum())
print(f"Inf records with Flow Duration == 0: {inf_zero_dur} / {len(inf_df)} ({round(inf_zero_dur/len(inf_df)*100, 2)}%)")

# 4. Cybersecurity Investigation: Botnet (ARES) Traffic
bot_df = df[df[label_col] == 'Bot']
benign_df = df[df[label_col] == 'BENIGN']

print(f"\n--- Botnet (ARES) Behavioral Profile ({len(bot_df)} records) ---")
bot_ports = bot_df['Destination Port'].value_counts()
print(f"Top Bot Destination Ports:\n{bot_ports.head(5)}")

bot_metrics = ['Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
               'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
               'Flow IAT Mean', 'Flow IAT Std', 'Flow IAT Max', 'Flow Packets/s', 'Flow Bytes/s']

bot_comp = []
for l in ['BENIGN', 'Bot']:
    sub = df[df[label_col] == l].replace([np.inf, -np.inf], np.nan)
    r = {"Class": l, "Count": len(sub)}
    for m in bot_metrics:
        r[f"{m}_mean"] = round(float(sub[m].mean()), 2)
        r[f"{m}_median"] = round(float(sub[f"{m}"].median()), 2)
    bot_comp.append(r)

bot_comp_df = pd.DataFrame(bot_comp)
print("\nBenign vs Bot Comparison (Medians):")
print(bot_comp_df[['Class', 'Flow Duration_median', 'Flow IAT Mean_median', 'Flow IAT Max_median', 'Total Fwd Packets_median', 'Total Backward Packets_median']])

# 5. Generate Figures
# Figure 1: Label Distribution
plt.figure(figsize=(7, 4.5))
ax = sns.barplot(x=label_counts.index, y=label_counts.values, palette=['#2b5c8f', '#984ea3'])
plt.title("Friday Morning: Class Distribution (Botnet ARES)", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count (log scale)", fontsize=11)
plt.yscale('log')
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_morning_label_distribution.png")
plt.close()

# Figure 2: Bot Destination Ports
plt.figure(figsize=(8, 4.5))
ax = sns.barplot(x=[str(p) for p in bot_ports.head(5).index], y=bot_ports.head(5).values, color='#984ea3')
plt.title("Friday Morning: Top Destination Ports Targeted by Botnet", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Destination Port", fontsize=11)
plt.ylabel("Flow Count", fontsize=11)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_morning_bot_ports.png")
plt.close()

# Figure 3: Flow IAT Mean Distribution (Log scale)
plt.figure(figsize=(9, 5))
df['log_Flow_IAT_Mean'] = np.log10(df['Flow IAT Mean'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_IAT_Mean', palette=['#2b5c8f', '#984ea3'])
plt.title("Friday Morning: Flow Inter-Arrival Time Mean (Beaconing Periodicity)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class", fontsize=11)
plt.ylabel("log10(Flow IAT Mean + 1 µs)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_morning_flow_iat_mean.png")
plt.close()

# Figure 4: Total Fwd vs Bwd Packets Scatter for Bot
plt.figure(figsize=(8, 6))
sample_plot = df.sample(n=min(10000, len(df)), random_state=42)
sns.scatterplot(data=sample_plot, x='Total Fwd Packets', y='Total Backward Packets', hue=label_col,
                palette={'BENIGN': '#a6cee3', 'Bot': '#984ea3'}, alpha=0.7, s=35)
plt.xlim(0, 50)
plt.ylim(0, 50)
plt.title("Friday Morning: Fwd vs Bwd Packet Symmetry in C2 Botnet Traffic", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Total Forward Packets", fontsize=11)
plt.ylabel("Total Backward Packets", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_morning_packet_symmetry.png")
plt.close()

# Save JSON results
friday_morning_results = {
    "dataset": "Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels": {k: int(v) for k, v in label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "bot_ports": {str(k): int(v) for k, v in bot_ports.items()}
}
with open("reports/friday_morning_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(friday_morning_results, f, indent=2)

print("\nFriday Morning Botnet analysis completed successfully.")
