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

fig_dir = "figures/friday_ddos"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
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

print(f"\n--- Baseline Quality (Friday DDoS) ---")
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

# 4. Cybersecurity Investigation: DDoS (LOIC) Dynamics
ddos_df = df[df[label_col] == 'DDoS']
benign_df = df[df[label_col] == 'BENIGN']

print(f"\n--- DDoS Attack Behavioral Profile ({len(ddos_df)} records) ---")
ddos_ports = ddos_df['Destination Port'].value_counts()
print(f"Top DDoS Destination Ports:\n{ddos_ports.head(5)}")

ddos_metrics = ['Flow Duration', 'Flow Packets/s', 'Flow Bytes/s', 'Total Fwd Packets',
                'Total Backward Packets', 'Fwd Packet Length Mean', 'Bwd Packet Length Mean',
                'Flow IAT Mean', 'Flow IAT Std']

ddos_comp = []
for l in ['BENIGN', 'DDoS']:
    sub = df[df[label_col] == l].replace([np.inf, -np.inf], np.nan)
    r = {"Class": l, "Count": len(sub)}
    for m in ddos_metrics:
        r[f"{m}_mean"] = round(float(sub[m].mean()), 2)
        r[f"{m}_median"] = round(float(sub[f"{m}"].median()), 2)
    ddos_comp.append(r)

ddos_comp_df = pd.DataFrame(ddos_comp)
print("\nBenign vs DDoS Comparison (Medians):")
print(ddos_comp_df[['Class', 'Flow Duration_median', 'Flow Packets/s_median', 'Flow Bytes/s_median', 'Total Fwd Packets_median', 'Total Backward Packets_median']])

# 5. Generate Figures
# Figure 1: Label Distribution
plt.figure(figsize=(7, 4.5))
ax = sns.barplot(x=label_counts.index, y=label_counts.values, palette=['#e41a1c', '#2b5c8f'])
plt.title("Friday Afternoon: DDoS Class Distribution", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count", fontsize=11)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_ddos_label_distribution.png")
plt.close()

# Figure 2: Packet Rate Distribution (Flow Packets/s Log Scale)
plt.figure(figsize=(9, 5))
valid_pkt_rate = df.replace([np.inf, -np.inf], np.nan).dropna(subset=['Flow Packets/s'])
valid_pkt_rate['log_Flow_Packets_s'] = np.log10(valid_pkt_rate['Flow Packets/s'].clip(lower=1))
sns.boxplot(data=valid_pkt_rate, x=label_col, y='log_Flow_Packets_s', palette=['#e41a1c', '#2b5c8f'])
plt.title("Friday Afternoon: Flow Packet Rate (log10 Packets/s) Comparison", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class", fontsize=11)
plt.ylabel("log10(Flow Packets/s + 1)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_ddos_packet_rate_distribution.png")
plt.close()

# Figure 3: Flow Duration Comparison (Boxplot log scale)
plt.figure(figsize=(9, 5))
df['log_Flow_Duration'] = np.log10(df['Flow Duration'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_Duration', palette=['#e41a1c', '#2b5c8f'])
plt.title("Friday Afternoon: Flow Duration (DDoS vs Benign)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class", fontsize=11)
plt.ylabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_ddos_duration_comparison.png")
plt.close()

# Figure 4: Fwd vs Bwd Packet Length Scatter for DDoS
plt.figure(figsize=(8, 6))
sample_ddos = df.sample(n=min(10000, len(df)), random_state=42)
sns.scatterplot(data=sample_ddos, x='Total Length of Fwd Packets', y='Total Length of Bwd Packets',
                hue=label_col, palette={'BENIGN': '#a6cee3', 'DDoS': '#e41a1c'}, alpha=0.6, s=30)
plt.title("Friday Afternoon: Request vs Response Payload Volume (DDoS vs Benign)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Total Length of Fwd Packets (bytes)", fontsize=11)
plt.ylabel("Total Length of Bwd Packets (bytes)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_ddos_payload_scatter.png")
plt.close()

# Save JSON results
friday_ddos_results = {
    "dataset": "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels": {k: int(v) for k, v in label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "ddos_ports": {str(k): int(v) for k, v in ddos_ports.items()}
}
with open("reports/friday_ddos_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(friday_ddos_results, f, indent=2)

print("\nFriday Afternoon DDoS analysis completed successfully.")
