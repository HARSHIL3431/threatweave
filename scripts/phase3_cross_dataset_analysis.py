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

fig_dir = "figures/combined"
os.makedirs(fig_dir, exist_ok=True)

dataset_dir = "dataset"
files = [
    ("Monday", "Monday-WorkingHours.pcap_ISCX.csv"),
    ("Tuesday", "Tuesday-WorkingHours.pcap_ISCX.csv"),
    ("Wednesday", "Wednesday-workingHours.pcap_ISCX.csv"),
    ("Thursday-Morning", "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"),
    ("Thursday-Afternoon", "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv"),
    ("Friday-Morning", "Friday-WorkingHours-Morning.pcap_ISCX.csv"),
    ("Friday-PortScan", "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv"),
    ("Friday-DDoS", "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv")
]

print("Starting Cross-Dataset Synthesis and Benign Drift Analysis...")

benign_samples = []
cross_inventory = []
label_aggregation = {}

key_features = [
    'Destination Port', 'Flow Duration', 'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets', 'Fwd Packet Length Mean',
    'Bwd Packet Length Mean', 'Flow Bytes/s', 'Flow Packets/s', 'Flow IAT Mean', 'Flow IAT Max',
    'Average Packet Size', 'Subflow Fwd Packets', 'Subflow Bwd Packets'
]

benign_summary_stats = []

for day_label, filename in files:
    filepath = os.path.join(dataset_dir, filename)
    print(f"Loading {day_label} ({filename})...")
    
    df = pd.read_csv(filepath, encoding='latin1', low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    
    # Resolve duplicate column
    cols = list(df.columns)
    if cols.count('Fwd Header Length') > 1:
        first_idx = cols.index('Fwd Header Length')
        second_idx = cols.index('Fwd Header Length', first_idx + 1)
        cols[second_idx] = 'Fwd Header Length.1'
        df.columns = cols
        
    label_col = 'Label'
    total_rows = len(df)
    
    # Clean and standardize labels
    raw_counts = df[label_col].value_counts()
    for raw_l, cnt in raw_counts.items():
        norm_l = str(raw_l).replace('\x96', '-').replace('ï¿½', '-').replace('\ufffd', '-').strip()
        label_aggregation[norm_l] = label_aggregation.get(norm_l, 0) + int(cnt)
        
    # Isolate Benign Traffic
    benign_mask = df[label_col].astype(str).str.contains('BENIGN', case=False)
    benign_df = df[benign_mask].copy()
    benign_count = len(benign_df)
    attack_count = total_rows - benign_count
    
    # Numeric conversion of key features
    for f in key_features:
        benign_df[f] = pd.to_numeric(benign_df[f], errors='coerce')
        
    # Calculate stats for benign drift
    b_stats = {
        "Day": day_label,
        "Total_Flows": total_rows,
        "Benign_Flows": benign_count,
        "Attack_Flows": attack_count,
        "Attack_Pct": round(attack_count / total_rows * 100, 2),
        "Duration_median": float(benign_df['Flow Duration'].median()),
        "Duration_mean": float(benign_df['Flow Duration'].mean()),
        "Fwd_Pkts_median": float(benign_df['Total Fwd Packets'].median()),
        "Bwd_Pkts_median": float(benign_df['Total Backward Packets'].median()),
        "Flow_IAT_Mean_median": float(benign_df['Flow IAT Mean'].median()),
        "Pkt_Size_mean": float(benign_df['Average Packet Size'].mean()),
        "DNS_Port53_Pct": round(float((benign_df['Destination Port'] == 53).mean() * 100), 2),
        "HTTPS_Port443_Pct": round(float((benign_df['Destination Port'] == 443).mean() * 100), 2),
        "HTTP_Port80_Pct": round(float((benign_df['Destination Port'] == 80).mean() * 100), 2)
    }
    benign_summary_stats.append(b_stats)
    
    # Take a stratified random sample of 5,000 benign records for combined plotting
    sample_b = benign_df[key_features].replace([np.inf, -np.inf], np.nan).dropna().sample(n=min(5000, len(benign_df)), random_state=42).copy()
    sample_b['Day'] = day_label
    benign_samples.append(sample_b)

benign_drift_df = pd.DataFrame(benign_summary_stats)
combined_benign_samples = pd.concat(benign_samples, ignore_index=True)

print("\n--- Benign Traffic Summary Across Days ---")
print(benign_drift_df[['Day', 'Benign_Flows', 'Attack_Pct', 'Duration_median', 'DNS_Port53_Pct', 'HTTPS_Port443_Pct', 'HTTP_Port80_Pct']])

print("\n--- Global Multi-Class Aggregation (All 8 Datasets) ---")
all_labels_df = pd.DataFrame(list(label_aggregation.items()), columns=['Class', 'Total_Count']).sort_values(by='Total_Count', ascending=False)
all_labels_df['Percentage'] = round(all_labels_df['Total_Count'] / all_labels_df['Total_Count'].sum() * 100, 4)
print(all_labels_df)

# Generate Figures
# Figure 1: Global Multiclass Label Distribution Log Scale
plt.figure(figsize=(12, 6))
ax = sns.barplot(data=all_labels_df, x='Class', y='Total_Count', palette='viridis')
plt.title("CICIDS2017 Suite: Master Label Distribution (2,830,743 Total Flows)", fontsize=13, fontweight='bold', pad=12)
plt.ylabel("Total Flow Count (log scale)", fontsize=11)
plt.yscale('log')
plt.xticks(rotation=30, ha='right')
for p in ax.patches:
    ax.annotate(f"{int(p.get_height()):,}", (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='bottom', fontsize=7.5, xytext=(0, 3), textcoords='offset points')
plt.tight_layout()
plt.savefig(f"{fig_dir}/combined_master_label_distribution.png")
plt.close()

# Figure 2: Benign Port Distribution Drift Across Days
port_drift_data = pd.melt(benign_drift_df, id_vars=['Day'], value_vars=['DNS_Port53_Pct', 'HTTPS_Port443_Pct', 'HTTP_Port80_Pct'],
                          var_name='Service', value_name='Percentage')
port_drift_data['Service'] = port_drift_data['Service'].map({
    'DNS_Port53_Pct': 'DNS (Port 53)',
    'HTTPS_Port443_Pct': 'HTTPS (Port 443)',
    'HTTP_Port80_Pct': 'HTTP (Port 80)'
})

plt.figure(figsize=(11, 5.5))
sns.barplot(data=port_drift_data, x='Day', y='Percentage', hue='Service', palette=['#1f77b4', '#2ca02c', '#ff7f0e'])
plt.title("Benign Traffic Drift: Service Port Proportions Across Days", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Recording Session (Day)", fontsize=11)
plt.ylabel("Percentage of Benign Flows (%)", fontsize=11)
plt.xticks(rotation=20, ha='right')
plt.legend(title="Service")
plt.tight_layout()
plt.savefig(f"{fig_dir}/combined_benign_port_drift.png")
plt.close()

# Figure 3: Benign Flow Duration Drift (Log scale boxplots across days)
combined_benign_samples['log_Flow_Duration'] = np.log10(combined_benign_samples['Flow Duration'].clip(lower=1))
plt.figure(figsize=(11, 5.5))
sns.boxplot(data=combined_benign_samples, x='Day', y='log_Flow_Duration', palette='crest')
plt.title("Benign Traffic Drift: Flow Duration Distribution Across Days", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Recording Session (Day)", fontsize=11)
plt.ylabel("log10(Flow Duration + 1 µs)", fontsize=11)
plt.xticks(rotation=20, ha='right')
plt.tight_layout()
plt.savefig(f"{fig_dir}/combined_benign_duration_drift.png")
plt.close()

# Figure 4: Benign Flow IAT Mean Drift
combined_benign_samples['log_Flow_IAT_Mean'] = np.log10(combined_benign_samples['Flow IAT Mean'].clip(lower=1))
plt.figure(figsize=(11, 5.5))
sns.boxplot(data=combined_benign_samples, x='Day', y='log_Flow_IAT_Mean', palette='magma')
plt.title("Benign Traffic Drift: Flow Inter-Arrival Time Mean Across Days", fontsize=13, fontweight='bold', pad=12)
plt.xlabel("Recording Session (Day)", fontsize=11)
plt.ylabel("log10(Flow IAT Mean + 1 µs)", fontsize=11)
plt.xticks(rotation=20, ha='right')
plt.tight_layout()
plt.savefig(f"{fig_dir}/combined_benign_iat_drift.png")
plt.close()

# Save cross dataset analysis JSON
cross_results = {
    "total_flows_all": int(all_labels_df['Total_Count'].sum()),
    "total_benign_flows": int(all_labels_df[all_labels_df['Class'] == 'BENIGN']['Total_Count'].iloc[0]),
    "total_attack_flows": int(all_labels_df[all_labels_df['Class'] != 'BENIGN']['Total_Count'].sum()),
    "benign_percentage": float(all_labels_df[all_labels_df['Class'] == 'BENIGN']['Percentage'].iloc[0]),
    "attack_percentage": float(all_labels_df[all_labels_df['Class'] != 'BENIGN']['Percentage'].sum()),
    "labels_breakdown": all_labels_df.to_dict(orient='records'),
    "benign_drift_by_day": benign_summary_stats
}
with open("reports/cross_dataset_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(cross_results, f, indent=2)

print("\nCross-Dataset Synthesis executed and figures saved successfully.")
