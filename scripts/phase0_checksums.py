import os
import hashlib
import datetime
import pandas as pd

dataset_dir = "dataset"
files = sorted([f for f in os.listdir(dataset_dir) if f.endswith(".csv")])

checksums_data = []

print(f"Found {len(files)} CSV files in {dataset_dir}. Calculating SHA-256 checksums...")

for filename in files:
    filepath = os.path.join(dataset_dir, filename)
    stat = os.stat(filepath)
    size_bytes = stat.st_size
    mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
    
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536 * 16), b""):
            sha256.update(chunk)
    digest = sha256.hexdigest()
    
    checksums_data.append({
        "Filename": filename,
        "Relative Path": filepath.replace("\\", "/"),
        "Size (Bytes)": size_bytes,
        "Size (MB)": round(size_bytes / (1024 * 1024), 2),
        "Modification Time": mtime,
        "SHA-256": digest
    })
    print(f"Computed: {filename} ({round(size_bytes / (1024 * 1024), 2)} MB) -> {digest}")

df_checksums = pd.DataFrame(checksums_data)

# Write reports/DATASET_CHECKSUMS.md
os.makedirs("reports", exist_ok=True)
with open("reports/DATASET_CHECKSUMS.md", "w", encoding="utf-8") as f:
    f.write("# CICIDS2017 Dataset Checksums & Integrity Manifest\n\n")
    f.write(f"Generated on: {datetime.datetime.now().isoformat()}\n\n")
    f.write("> [!IMPORTANT]\n")
    f.write("> These SHA-256 checksums establish the baseline integrity of all original CSV files. Original files must remain unmodified throughout the EDA.\n\n")
    f.write("| Filename | Size (MB) | Size (Bytes) | Modification Time | SHA-256 Checksum |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- |\n")
    for row in checksums_data:
        f.write(f"| `{row['Filename']}` | {row['Size (MB)']} | {row['Size (Bytes)']:,} | `{row['Modification Time']}` | `{row['SHA-256']}` |\n")

print("reports/DATASET_CHECKSUMS.md successfully written.")
