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

fig_dir = "figures/tuesday"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Tuesday-WorkingHours.pcap_ISCX.csv"
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

print(f"\n--- Baseline Quality (Tuesday) ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Labels & Imbalance
label_counts = df[label_col].value_counts()
print(f"\n--- Label Breakdown ---")
for k, v in label_counts.items():
    print(f"  - {k}: {v:,} ({round(v/total_rows*100, 4)}%)")

# 3. Inf Root-Cause & Attack association
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
inf_df = df[inf_mask]
print(f"\nInf values by Label: {inf_df[label_col].value_counts().to_dict()}")
inf_zero_dur = int((inf_df['Flow Duration'] == 0).sum())
print(f"Inf records with Flow Duration == 0: {inf_zero_dur} / {len(inf_df)} ({round(inf_zero_dur/len(inf_df)*100, 2)}%)")

# 4. Cybersecurity Hypothesis Investigation: Brute-Force Patator Attacks
print(f"\n--- Cybersecurity Investigation: FTP-Patator & SSH-Patator ---")

# Check targeted destination ports
ports_by_label = df.groupby(label_col)['Destination Port'].value_counts()
print("Destination Ports targeted by each class:")
for l in label_counts.index:
    print(f"[{l}] Top Ports:\n{ports_by_label.get(l, pd.Series()).head(3)}")

# Behavior comparison between Benign, FTP-Patator, SSH-Patator
behavior_features = ['Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
                     'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
                     'Flow Packets/s', 'Flow Bytes/s', 'Flow IAT Mean', 'Fwd Packet Length Mean']

comp_data = []
for l in label_counts.index:
    sub = df[df[label_col] == l].replace([np.inf, -np.inf], np.nan)
    row = {"Class": l, "Count": len(sub)}
    for f in behavior_features:
        row[f"{f}_mean"] = round(float(sub[f].mean()), 2)
        row[f"{f}_median"] = round(float(sub[f].median()), 2)
    comp_data.append(row)

comp_df = pd.DataFrame(comp_data)
print("\nFeature Comparison by Class (Means & Medians):")
print(comp_df[['Class', 'Flow Duration_median', 'Total Fwd Packets_median', 'Total Backward Packets_median', 'Total Length of Fwd Packets_median', 'Total Length of Bwd Packets_median']])

# Compare Benign traffic on Port 21/22 vs Patator traffic on Port 21/22
benign_p21 = df[(df[label_col] == 'BENIGN') & (df['Destination Port'] == 21)]
ftp_pat = df[df[label_col] == 'FTP-Patator']
benign_p22 = df[(df[label_col] == 'BENIGN') & (df['Destination Port'] == 22)]
ssh_pat = df[df[label_col] == 'SSH-Patator']

print(f"\nBenign on Port 21: {len(benign_p21):,} flows | FTP-Patator on Port 21: {len(ftp_pat):,} flows")
print(f"Benign on Port 22: {len(benign_p22):,} flows | SSH-Patator on Port 22: {len(ssh_pat):,} flows")

# 5. Generate Figures
# Figure 1: Label Distribution
plt.figure(figsize=(8, 4.5))
ax = sns.barplot(x=label_counts.index, y=label_counts.values, palette=['#2b5c8f', '#d95f02', '#7570b3'])
plt.title("Tuesday: Flow Count by Class (FTP & SSH Patator)", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count", fontsize=11)
plt.yscale('log')
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/tuesday_label_distribution.png")
plt.close()

# Figure 2: Flow Duration Comparison (Boxplot log scale)
plt.figure(figsize=(9, 5))
df['log_Flow_Duration'] = np.log10(df['Flow Duration'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_Duration', palette=['#2b5c8f', '#d95f02', '#7570b3'])
plt.title("Tuesday: Flow Duration Comparison by Class", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class Label", fontsize=11)
plt.ylabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/tuesday_flow_duration_by_class.png")
plt.close()

# Figure 3: Packet Count Symmetry (Fwd vs Bwd Packets)
plt.figure(figsize=(9, 6))
sample_plot = df.sample(n=min(15000, len(df)), random_state=42)
sns.scatterplot(data=sample_plot, x='Total Fwd Packets', y='Total Backward Packets', hue=label_col, alpha=0.6,
                palette={'BENIGN': '#a6cee3', 'FTP-Patator': '#e31a1c', 'SSH-Patator': '#ff7f00'}, s=30)
plt.xlim(0, 100)
plt.ylim(0, 100)
plt.title("Tuesday: Forward vs Backward Packet Count Symmetry", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Total Forward Packets", fontsize=11)
plt.ylabel("Total Backward Packets", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/tuesday_packet_symmetry.png")
plt.close()

# Figure 4: Forward Packet Length Mean Distribution
plt.figure(figsize=(9, 5))
sns.kdeplot(data=df[df[label_col] == 'BENIGN']['Fwd Packet Length Mean'].clip(upper=1000), label='BENIGN', fill=True, alpha=0.3, color='#2b5c8f')
sns.kdeplot(data=df[df[label_col] == 'FTP-Patator']['Fwd Packet Length Mean'].clip(upper=1000), label='FTP-Patator', fill=True, alpha=0.3, color='#d95f02')
sns.kdeplot(data=df[df[label_col] == 'SSH-Patator']['Fwd Packet Length Mean'].clip(upper=1000), label='SSH-Patator', fill=True, alpha=0.3, color='#7570b3')
plt.title("Tuesday: Fwd Packet Length Mean Density Comparison", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Fwd Packet Length Mean (bytes)", fontsize=11)
plt.legend()
plt.tight_layout()
plt.savefig(f"{fig_dir}/tuesday_fwd_pkt_length_density.png")
plt.close()

# Save JSON results
tuesday_results = {
    "dataset": "Tuesday-WorkingHours.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels": {k: int(v) for k, v in label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "inf_zero_dur": inf_zero_dur,
    "benign_p21": len(benign_p21),
    "ftp_pat_p21": len(ftp_pat),
    "benign_p22": len(benign_p22),
    "ssh_pat_p22": len(ssh_pat)
}
with open("reports/tuesday_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(tuesday_results, f, indent=2)

print("\nTuesday analysis executed successfully.")
