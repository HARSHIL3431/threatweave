import pandas as pd
import numpy as np

print("Loading dataset...")
df = pd.read_csv("data/combined/CICIDS2017_COMBINED_RAW.csv", low_memory=False)

feature_cols = [c for c in df.columns if c not in ['Source_File', 'Source_Day', 'Source_Row_Index', 'Label']]

print("Finding duplicates...")
# Group by features and check unique labels
df_hash = pd.util.hash_pandas_object(df[feature_cols], index=False)
df['_hash'] = df_hash

hash_labels = df.groupby('_hash')['Label'].nunique()
conflicting_hashes = hash_labels[hash_labels > 1].index

print(f"Number of feature vectors with conflicting labels: {len(conflicting_hashes)}")
if len(conflicting_hashes) > 0:
    conflicts = df[df['_hash'].isin(conflicting_hashes)]
    print("\nConflict Examples:")
    for h in conflicting_hashes[:5]:
        subset = conflicts[conflicts['_hash'] == h]
        print(f"Hash {h}:")
        print(subset['Label'].value_counts())

print("\nZero Duration vs Inf check...")
inf_bytes = np.isinf(df['Flow Bytes/s'].astype(float))
print("Labels for Inf Flow Bytes/s:")
print(df[inf_bytes]['Label'].value_counts())

print("\nNaN check...")
nan_bytes = df['Flow Bytes/s'].isna()
print("Labels for NaN Flow Bytes/s:")
print(df[nan_bytes]['Label'].value_counts())

