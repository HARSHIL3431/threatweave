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

fig_dir = "figures/thursday_webattacks"
os.makedirs(fig_dir, exist_ok=True)

csv_path = "dataset/Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"
print(f"Loading {csv_path}...")

# Load using latin1 to safely parse raw bytes
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

print(f"\n--- Baseline Quality (Thursday WebAttacks) ---")
print(f"Total Rows: {total_rows:,}")
print(f"Duplicate Rows: {dup_rows:,} ({dup_pct}%)")
print(f"Columns with NaNs: {cols_with_nan}")
print(f"Columns with Infs: {inf_counts}")

# 2. Label Encoding Inspection & Normalization
raw_labels = df[label_col].value_counts()
print(f"\n--- Raw Label Representation ---")
label_mapping = {}
for k, v in raw_labels.items():
    raw_str = str(k)
    hex_repr = raw_str.encode('latin1', errors='replace').hex()
    # Normalize for analysis display
    norm_str = raw_str.replace('\x96', '-').replace('ï¿½', '-').replace('\ufffd', '-').strip()
    label_mapping[raw_str] = norm_str
    print(f"  Raw: {repr(raw_str)} | Hex: {hex_repr} | Norm: '{norm_str}' | Count: {v:,}")

# Create normalized analysis label column without mutating original
df['Normalized_Label'] = df[label_col].map(label_mapping)
norm_label_counts = df['Normalized_Label'].value_counts()

# 3. Inf Root-Cause & Attack association
inf_mask = np.isinf(df['Flow Bytes/s']) | np.isinf(df['Flow Packets/s'])
inf_df = df[inf_mask]
print(f"\nInf values by Label: {inf_df['Normalized_Label'].value_counts().to_dict()}")
inf_zero_dur = int((inf_df['Flow Duration'] == 0).sum())
print(f"Inf records with Flow Duration == 0: {inf_zero_dur} / {len(inf_df)} ({round(inf_zero_dur/len(inf_df)*100, 2)}%)")

# 4. Cybersecurity Investigation: Web Attacks (Brute Force, XSS, Sql Injection)
print(f"\n--- Cybersecurity Investigation: Web Attacks ---")

# Targeted Destination Ports
ports_by_label = df.groupby('Normalized_Label')['Destination Port'].value_counts()
print("\nDestination Ports by Web Attack:")
for l in norm_label_counts.index:
    print(f"[{l}] Ports:\n{ports_by_label.get(l, pd.Series()).head(3)}")

# Detailed behavioral feature comparison
web_features = ['Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
                'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
                'Fwd Packet Length Mean', 'Bwd Packet Length Mean', 'Flow Bytes/s', 'Flow Packets/s']

web_comp = []
for l in norm_label_counts.index:
    sub = df[df['Normalized_Label'] == l].replace([np.inf, -np.inf], np.nan)
    r = {"Class": l, "Count": len(sub)}
    for f in web_features:
        r[f"{f}_mean"] = round(float(sub[f].mean()), 2)
        r[f"{f}_median"] = round(float(sub[f].median()), 2)
    web_comp.append(r)

web_comp_df = pd.DataFrame(web_comp)
print("\nWeb Attack Behavioral Comparison (Medians):")
print(web_comp_df[['Class', 'Flow Duration_median', 'Total Fwd Packets_median', 'Total Backward Packets_median', 'Total Length of Fwd Packets_median', 'Total Length of Bwd Packets_median']])

# Sql Injection Deep Dive (21 instances)
sqli_df = df[df['Normalized_Label'] == 'Web Attack - Sql Injection']
print("\nSQL Injection Flow Profile (21 records):")
print(f"Duration median: {sqli_df['Flow Duration'].median():.1f} µs | Mean: {sqli_df['Flow Duration'].mean():.1f} µs")
print(f"Fwd Packets median: {sqli_df['Total Fwd Packets'].median()} | Bwd Packets median: {sqli_df['Total Backward Packets'].median()}")
print(f"Fwd Length median: {sqli_df['Total Length of Fwd Packets'].median()} bytes | Bwd Length median: {sqli_df['Total Length of Bwd Packets'].median()} bytes")

# 5. Generate Figures
# Figure 1: Web Attack Class Distribution Log Scale
plt.figure(figsize=(9, 5))
ax = sns.barplot(x=norm_label_counts.index, y=norm_label_counts.values, palette='Set2')
plt.title("Thursday Morning: Web Attacks Class Distribution", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Flow Count (log scale)", fontsize=11)
plt.yscale('log')
plt.xticks(rotation=15, ha='right')
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=9, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/thursday_webattacks_label_distribution.png")
plt.close()

# Figure 2: Total Length of Fwd Packets (Payload size comparison)
plt.figure(figsize=(10, 5.5))
df['log_Fwd_Length'] = np.log10(df['Total Length of Fwd Packets'].clip(lower=1))
sns.boxplot(data=df, x='Normalized_Label', y='log_Fwd_Length', palette='Set2')
plt.title("Thursday Morning: Total Fwd Packet Length (Request Payload Size) by Class", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Class", fontsize=11)
plt.ylabel("log10(Total Fwd Length + 1 bytes)", fontsize=11)
plt.xticks(rotation=15, ha='right')
plt.tight_layout()
plt.savefig(f"{fig_dir}/thursday_webattacks_fwd_payload_length.png")
plt.close()

# Figure 3: Fwd vs Bwd Packet Length Scatter
plt.figure(figsize=(9, 6))
sample_web = df[df['Normalized_Label'] != 'BENIGN'].copy()
sns.scatterplot(data=sample_web, x='Total Length of Fwd Packets', y='Total Length of Bwd Packets',
                hue='Normalized_Label', style='Normalized_Label', s=45, alpha=0.8, palette='Set1')
plt.title("Thursday Morning: Request vs Response Payload Sizes for Web Attacks", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Total Forward Length (Request Payload bytes)", fontsize=11)
plt.ylabel("Total Backward Length (Response Payload bytes)", fontsize=11)
plt.tight_layout()
plt.savefig(f"{fig_dir}/thursday_webattacks_request_response_scatter.png")
plt.close()

# Save JSON results
thursday_web_results = {
    "dataset": "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "total_rows": total_rows,
    "labels_raw": {repr(k): int(v) for k, v in raw_labels.items()},
    "labels_normalized": {k: int(v) for k, v in norm_label_counts.items()},
    "duplicate_rows": dup_rows,
    "duplicate_pct": dup_pct,
    "cols_with_nan": cols_with_nan,
    "cols_with_inf": inf_counts,
    "inf_zero_dur": inf_zero_dur,
    "sqli_count": len(sqli_df)
}
with open("reports/thursday_webattacks_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(thursday_web_results, f, indent=2)

print("\nThursday Morning Web Attacks analysis completed successfully.")
