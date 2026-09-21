# CICIDS2017 Preprocessing Recommendations

## 1. Executive Summary
This document provides evidence-based preprocessing specifications derived directly from our iterative EDA findings across all 8 CICIDS2017 datasets. These recommendations are designed to prevent data leakage, stabilize numerical calculations, and prepare clean feature matrices for both unsupervised (Isolation Forest) and supervised anomaly detection pipelines.

---

## 2. Step-by-Step Preprocessing Pipeline

### Step 1: Header Cleaning & Schema Standardization
- **Action 1**: Apply `df.columns = df.columns.str.strip()` to eliminate leading/trailing whitespace inconsistencies.
- **Action 2**: Drop duplicate column at index 34 (`Fwd Header Length.1`).
- **Action 3**: Map raw non-ASCII label strings in Thursday Web Attacks:
  ```python
  label_mapping = {
      'Web Attack \x96 Brute Force': 'Web Attack - Brute Force',
      'Web Attack \x96 XSS': 'Web Attack - XSS',
      'Web Attack \x96 Sql Injection': 'Web Attack - Sql Injection'
  }
  df['Label'] = df['Label'].replace(label_mapping).str.strip()
  ```

---

### Step 2: Deterministic Infinite (+Inf) & Missing (NaN) Resolution
- **Root Cause Established in EDA**: 100.0% of `+Inf` values in `Flow Packets/s` and `Flow Bytes/s` occur when `Flow Duration == 0`.
- **Recommended Strategy**:
  1. For zero-duration flows, impute a nominal duration of $1.0\ \mu\text{s}$ before computing rates:
     $$\text{Flow Packets/s} = \frac{\text{Total Packets}}{\max(\text{Flow Duration}, 1.0) \times 10^{-6}}$$
     $$\text{Flow Bytes/s} = \frac{\text{Total Bytes}}{\max(\text{Flow Duration}, 1.0) \times 10^{-6}}$$
  2. For missing values (`NaN` in `Flow Bytes/s`), impute using the training set median.

---

### Step 3: Constant Feature Elimination
Drop the 8 zero-variance features that provide no information across all 2.83M records:
```python
constant_features_to_drop = [
    'Bwd PSH Flags', 'Bwd URG Flags',
    'Fwd Avg Bytes/Bulk', 'Fwd Avg Packets/Bulk', 'Fwd Avg Bulk Rate',
    'Bwd Avg Bytes/Bulk', 'Bwd Avg Packets/Bulk', 'Bwd Avg Bulk Rate'
]
df = df.drop(columns=constant_features_to_drop)
```
Additionally drop `Fwd URG Flags` and `CWE Flag Count` if strict non-zero variance filtering ($>0.001$) is required.

---

### Step 4: Redundancy & Multicollinearity Pruning
For models sensitive to multicollinearity (linear models, neural nets), drop mathematically duplicate pairs ($r = 1.0000$):
- Drop `Avg Bwd Segment Size` (identical to `Bwd Packet Length Mean`).
- Drop `Avg Fwd Segment Size` (identical to `Fwd Packet Length Mean`).
- Drop `Subflow Fwd Packets` (identical to `Total Fwd Packets`).
- Drop `Subflow Bwd Packets` (identical to `Total Backward Packets`).
- Drop `Subflow Fwd Bytes` (identical to `Total Length of Fwd Packets`).
- Drop `Subflow Bwd Bytes` (identical to `Total Length of Bwd Packets`).
- Drop `SYN Flag Count` (identical to `Fwd PSH Flags`).

---

### Step 5: Duplicate Flow Removal (Leakage Prevention)
- **Recommendation**: Apply `df = df.drop_duplicates()` on the training dataset.
- For PortScan and DoS Hulk, deduplication removes over 72,000 artificial clones, ensuring test evaluation reflects generalization to unseen network flows rather than rote memorization.

---

### Step 6: Heavy-Tail Log Transformations & Robust Scaling
1. Apply $\log_{10}(x + 1)$ transformation to heavy-tailed volumetric and duration features:
   - `Flow Duration`, `Flow Bytes/s`, `Flow Packets/s`
   - `Total Fwd Packets`, `Total Backward Packets`
   - `Total Length of Fwd Packets`, `Total Length of Bwd Packets`
   - `Flow IAT Mean`, `Flow IAT Max`, `Flow IAT Std`
2. Follow with `RobustScaler` (scaling by median and IQR) fitted **strictly on the training split**.

---

### Step 7: Destination Port Strategy
- To evaluate true behavioral anomaly detection independent of testbed server IP/port configurations, evaluate models with `Destination Port` excluded from the feature matrix.

---

## 3. Summary Pipeline Execution Template
```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.impute import SimpleImputer

# Encapsulate all transformations in a leak-free Scikit-Learn pipeline
preprocessor = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', RobustScaler())
])
```
