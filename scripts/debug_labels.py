"""Quick diagnostic: print the raw hex bytes of all unique labels in Thursday Web Attacks."""
import pandas as pd
import sys, os

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

filepath = "dataset/Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv"
df = pd.read_csv(filepath, encoding='utf-8', low_memory=False)
df.columns = df.columns.str.strip()
labels = df['Label'].astype(str).str.strip().unique()

print(f"Total unique labels: {len(labels)}")
for label in sorted(labels):
    hex_repr = label.encode('utf-8').hex()
    print(f"  Label: repr={repr(label)}")
    print(f"         hex={hex_repr}")
    print(f"         len={len(label)}")
    print()

# Try latin-1 encoding
print("\n--- Reading with latin-1 encoding ---")
df2 = pd.read_csv(filepath, encoding='latin-1', low_memory=False)
df2.columns = df2.columns.str.strip()
labels2 = df2['Label'].astype(str).str.strip().unique()

print(f"Total unique labels: {len(labels2)}")
for label in sorted(labels2):
    hex_repr = label.encode('latin-1', errors='replace').hex()
    print(f"  Label: repr={repr(label)}")
    print(f"         hex_latin1={hex_repr}")
    print(f"         hex_utf8={label.encode('utf-8').hex()}")
    print()
