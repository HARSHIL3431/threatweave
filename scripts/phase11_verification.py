import os
import sys
import hashlib
import json
import pandas as pd

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("Starting Phase 11 Reproducibility and Integrity Verification...")

# 1. Recalculate SHA-256 Checksums
dataset_dir = "dataset"
files = sorted([f for f in os.listdir(dataset_dir) if f.endswith(".csv")])

with open("reports/DATASET_CHECKSUMS.md", "r", encoding="utf-8") as f:
    checksums_md = f.read()

checksum_mismatches = 0
print("\n--- Verifying Original CSV Integrity (SHA-256) ---")
for filename in files:
    filepath = os.path.join(dataset_dir, filename)
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536 * 16), b""):
            sha256.update(chunk)
    digest = sha256.hexdigest()
    
    if digest in checksums_md:
        print(f"PASS: {filename} matches baseline SHA-256 ({digest[:12]}...)")
    else:
        print(f"FAIL: {filename} checksum MISMATCH!")
        checksum_mismatches += 1

if checksum_mismatches == 0:
    print("\nVERDICT: 100% INTEGRITY VERIFIED - NO ORIGINAL CSV WAS MODIFIED.")
else:
    print(f"\nERROR: {checksum_mismatches} files modified!")

# 2. Verify all expected reports exist
expected_reports = [
    "DATASET_CHECKSUMS.md",
    "DATASET_INVENTORY.md",
    "DATASET_INVENTORY.csv",
    "DATASET_QUALITY_REPORT.md",
    "SCHEMA_COMPATIBILITY_REPORT.md",
    "Monday_EDA_REPORT.md",
    "Tuesday_EDA_REPORT.md",
    "Wednesday_EDA_REPORT.md",
    "Thursday_WebAttacks_EDA_REPORT.md",
    "Thursday_Infiltration_EDA_REPORT.md",
    "Friday_Morning_EDA_REPORT.md",
    "Friday_PortScan_EDA_REPORT.md",
    "Friday_DDoS_EDA_REPORT.md",
    "CROSS_DATASET_ANALYSIS.md",
    "DATA_LEAKAGE_AUDIT.md",
    "ISOLATION_FOREST_READINESS.md",
    "PREPROCESSING_RECOMMENDATIONS.md",
    "CICIDS2017_EDA_FINAL_REPORT.md"
]

print("\n--- Verifying Report Deliverables ---")
missing_reports = 0
for r in expected_reports:
    path = os.path.join("reports", r)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"PASS: reports/{r} exists ({os.path.getsize(path):,} bytes)")
    else:
        print(f"FAIL: reports/{r} MISSING or EMPTY!")
        missing_reports += 1

# 3. Verify all expected notebooks exist
expected_notebooks = [
    "Dataset_1_Monday_EDA.ipynb",
    "Dataset_2_Tuesday_EDA.ipynb",
    "Dataset_3_Wednesday_EDA.ipynb",
    "Dataset_4_Thursday_WebAttacks_EDA.ipynb",
    "Dataset_5_Thursday_Infiltration_EDA.ipynb",
    "Dataset_6_Friday_Morning_EDA.ipynb",
    "Dataset_7_Friday_PortScan_EDA.ipynb",
    "Dataset_8_Friday_DDoS_EDA.ipynb",
    "CICIDS2017_Combined_EDA.ipynb"
]

print("\n--- Verifying Jupyter Notebooks ---")
missing_notebooks = 0
for nb in expected_notebooks:
    path = os.path.join("notebooks", nb)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"PASS: notebooks/{nb} exists ({os.path.getsize(path):,} bytes)")
    else:
        print(f"FAIL: notebooks/{nb} MISSING or EMPTY!")
        missing_notebooks += 1

# 4. Verify figures
figure_dirs = [
    "monday", "tuesday", "wednesday", "thursday_webattacks", "thursday_infiltration",
    "friday_morning", "friday_portscan", "friday_ddos", "combined"
]
print("\n--- Verifying Generated Figures ---")
total_figs = 0
for fd in figure_dirs:
    path = os.path.join("figures", fd)
    figs = [f for f in os.listdir(path) if f.endswith(".png")]
    total_figs += len(figs)
    print(f"figures/{fd}: {len(figs)} figures ({', '.join(figs)})")

print(f"\nTotal figures generated: {total_figs}")

if checksum_mismatches == 0 and missing_reports == 0 and missing_notebooks == 0:
    print("\nALL VERIFICATION CHECKS PASSED PERFECTLY!")
