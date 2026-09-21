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

fig_dir = "figures/friday_portscan"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"
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

print(f"\n--- Baseline Quality (Friday PortScan) ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Labels
label_counts = df[label_col].value_counts()
print(f"\n--- Label Breakdown ---")
for k, v in label_counts.items():
    print(f"  - {k}: {v:,} ({round(v/total_rows*100, 4)}%)")

# 3. Investigation of Duplicate Rate & Single-Packet Scans
scan_df = df[df[label_col] == 'PortScan']
benign_df = df[df[label_col] == 'BENIGN']

scan_dups = int(scan_df.duplicated().sum())
benign_dups = int(benign_df.duplicated().sum())
print(f"\nDuplicate Breakdown:")
print(f"  - In PortScan: {scan_dups:,} / {len(scan_df):,} ({round(scan_dups/len(scan_df)*100, 2)}%)")
print(f"  - In BENIGN: {benign_dups:,} / {len(benign_df):,} ({round(benign_dups/len(benign_df)*100, 2)}%)")

# Check Single-Packet and Forward-Only Flows in PortScan
scan_1pkt = int((scan_df['Total Fwd Packets'] == 1).sum())
scan_0bwd = int((scan_df['Total Backward Packets'] == 0).sum())
scan_0dur = int((scan_df['Flow Duration'] == 0).sum())
print(f"\nPortScan Behavioral Mechanics:")
print(f"  - Flows with Total Fwd Packets == 1: {scan_1pkt:,} ({round(scan_1pkt/len(scan_df)*100, 2)}%)")
print(f"  - Flows with Total Backward Packets == 0 (Unanswered probes): {scan_0bwd:,} ({round(scan_0bwd/len(scan_df)*100, 2)}%)")
print(f"  - Flows with Flow Duration == 0: {scan_0dur:,} ({round(scan_0dur/len(scan_df)*100, 2)}%)")

# Unique Destination Ports Probed
unique_scan_ports = scan_df['Destination Port'].nunique()
unique_benign_ports = benign_df['Destination Port'].nunique()
print(f"\nPort Diversity:")
print(f"  - Unique Destination Ports in PortScan: {unique_scan_ports:,}")
print(f"  - Unique Destination Ports in BENIGN: {unique_benign_ports:,}")

# Inf Root-Cause
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
inf_df = df[inf_mask]
print(f"\nInf values by Label: {inf_df[label_col].value_counts().to_dict()}")
inf_zero_dur = int((inf_df['Flow Duration'] == 0).sum())
print(f"Inf records with Flow Duration == 0: {inf_zero_dur} / {len(inf_df)} ({round(inf_zero_dur/len(inf_df)*100, 2)}%)")

# Flag Analysis (RST, SYN, FIN, PSH, ACK)
flag_cols = ['FIN Flag Count', 'SYN Flag Count', 'RST Flag Count', 'PSH Flag Count', 'ACK Flag Count', 'URG Flag Count', 'ECE Flag Count']
print("\nFlag Counts in PortScan vs Benign:")
flag_comp = []
for f in flag_cols:
    flag_comp.append({
        "Flag": f,
        "PortScan_Mean": round(float(scan_df[f].mean()), 4),
        "Benign_Mean": round(float(benign_df[f].mean()), 4)
    })
print(pd.DataFrame(flag_comp))

# 4. Generate Figures
# Figure 1: Class Distribution
plt.figure(figsize=(7, 4.5))
ax = sns.barplot(x=label_counts.index, y=label_counts.values, palette=['#e41a1c', '#2b5c8f'])
plt.title("Friday Afternoon: PortScan Class Distribution", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count", fontsize=11)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_portscan_label_distribution.png")
plt.close()

# Figure 2: Destination Port Distribution Histogram
plt.figure(figsize=(10, 5))
sns.histplot(scan_df['Destination Port'], bins=60, color='#e41a1c', label='PortScan (Scanning range)')
sns.histplot(benign_df['Destination Port'], bins=60, color='#2b5c8f', alpha=0.4, label='BENIGN')
plt.title("Friday Afternoon: Destination Port Distribution (Port Scanning Spectrum)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Destination Port Number (0 - 65535)", fontsize=11)
plt.ylabel("Flow Count", fontsize=11)
plt.legend()
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_portscan_port_spectrum.png")
plt.close()

# Figure 3: Flow Duration Comparison (Boxplot log scale)
plt.figure(figsize=(8, 5))
df['log_Flow_Duration'] = np.log10(df['Flow Duration'].clip(lower=1))
sns.boxplot(data=df, x=label_col, y='log_Flow_Duration', palette=['#e41a1c', '#2b5c8f'])
plt.title("Friday Afternoon: Flow Duration (PortScan vs Benign)", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class", fontsize=11)
plt.ylabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_portscan_duration_comparison.png")
plt.close()

# Figure 4: Packet Count Distribution (1-Packet Probes)
plt.figure(figsize=(8, 4.5))
pkt_df = pd.DataFrame({
    'Total Fwd Packets': ['1 Packet Probe', '2 Packets', '>= 3 Packets'],
    'PortScan Count': [
        int((scan_df['Total Fwd Packets'] == 1).sum()),
        int((scan_df['Total Fwd Packets'] == 2).sum()),
        int((scan_df['Total Fwd Packets'] >= 3).sum())
    ]
})
ax = sns.barplot(data=pkt_df, x='Total Fwd Packets', y='PortScan Count', color='#e41a1c')
plt.title("PortScan Flow Profile: Prevalence of 1-Packet Probes", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count", fontsize=11)
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/friday_portscan_1pkt_probes.png")
plt.close()

# Save JSON results
friday_portscan_results = {
    "dataset": "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels": {k: int(v) for k, v in label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "scan_dups": scan_dups,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "unique_scan_ports": unique_scan_ports,
    "scan_1pkt_pct": round(scan_1pkt/len(scan_df)*100, 2),
    "scan_0bwd_pct": round(scan_0bwd/len(scan_df)*100, 2),
    "scan_0dur_pct": round(scan_0dur/len(scan_df)*100, 2)
}
with open("reports/friday_portscan_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(friday_portscan_results, f, indent=2)

print("\nFriday Afternoon PortScan analysis completed successfully.")
