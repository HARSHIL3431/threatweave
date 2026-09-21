# CICIDS2017 Combined Preprocessing Pipeline Design

## 1. Executive Summary
This document specifies the data preprocessing pipeline designed for the **Combined CICIDS2017 Dataset (2.83M rows)**. It is based directly on the empirical findings from our Phase 5 Combined Exploratory Data Analysis. The design focuses heavily on resolving data leakage, preventing ML model memorization, mitigating mathematical undefined values (`NaN`/`Inf`), and preparing the feature matrix for unsupervised anomaly detection (specifically Isolation Forest).

---

## 2. Leakage Mitigation & Duplicate Handling

> [!CRITICAL]
> **Duplicate Row Hazard:** The combined dataset contains **308,381 removable duplicate rows** (10.89% of the dataset), comprising both intra-dataset clones and **139,843 inter-dataset clones** (benign/attack flows mathematically identical across different days). 

**Recommendation:**
- Apply `df = df.drop_duplicates(subset=feature_columns)` immediately after loading the combined dataset. 
- *Why:* Failing to deduplicate will leak training examples into the test set during partitioning, resulting in falsely inflated F1-scores.

> [!WARNING]
> **Environmental Port Leakage:** Certain attacks are 100% correlated to specific testbed destination ports (e.g., FTP-Patator on 21, SSH-Patator on 22, DoS attacks on 80).

**Recommendation:**
- Drop `Destination Port` from the feature matrix before training behavioral models, OR evaluate the model with and without this feature to quantify how much performance is derived from port memorization rather than flow behavior.

---

## 3. Data Quality Rectification (Inf / NaN)

Based on Section 6 of the Combined EDA, we observed:
- `2,867` rows with `Inf` in `Flow Bytes/s` or `Flow Packets/s`. **100%** of these are caused by `Flow Duration == 0`.
- `1,358` rows with `NaN` in `Flow Bytes/s`.

**Resolution Strategy (Pipeline Safe):**
1. **Inf Handling**: Replace `Inf` values by calculating an imputed rate. Temporarily replace 0-duration flows with $1.0\ \mu\text{s}$ to mathematically stabilize the denominator.
   ```python
   # Replace inf with upper bound rate based on 1us duration
   df.loc[df['Flow Duration'] == 0, 'Flow Duration'] = 1
   ```
2. **NaN Handling**: Use a `SimpleImputer(strategy='median')` fitted **strictly on the training split** to resolve the 1,358 NaN values.

---

## 4. Feature Space Reduction

To prevent multicollinearity, improve matrix conditioning, and accelerate training, we must drop uninformative and perfectly redundant features.

### 4.1 Drop Constant Features
Drop these 8 features as they possess zero variance (constant 0) across all 2.83 million rows:
- `Bwd PSH Flags`
- `Bwd URG Flags`
- `Fwd Avg Bytes/Bulk`
- `Fwd Avg Packets/Bulk`
- `Fwd Avg Bulk Rate`
- `Bwd Avg Bytes/Bulk`
- `Bwd Avg Packets/Bulk`
- `Bwd Avg Bulk Rate`

### 4.2 Drop Perfectly Correlated Redundancies
Drop these 10 features which exhibit Pearson $r = 1.0000$ with another feature in the dataset:
- `SYN Flag Count`
- `CWE Flag Count`
- `ECE Flag Count`
- `Bwd Header Length`
- `Avg Bwd Segment Size`
- `Avg Fwd Segment Size`
- `Subflow Fwd Packets`
- `Subflow Bwd Packets`
- `Subflow Fwd Bytes`
- `Subflow Bwd Bytes`

**Result:** The numerical feature space is reduced from 77 down to **59 usable features**.

---

## 5. Scaling and Transformation

Network traffic volume features (`Flow Bytes/s`, `Total Length of Fwd Packets`) exhibit extreme heavy-tail distributions with skewness values exceeding 800.

**Recommendation:**
1. **Log Transformation:** Apply $\log_{10}(x+1)$ to all byte/packet volume, rate, and duration features to compress the heavy tails.
2. **Robust Scaling:** Follow the log transformation with Scikit-Learn's `RobustScaler()` (which scales using the median and Interquartile Range) rather than `StandardScaler()`. This prevents the extreme DoS/PortScan outliers from corrupting the scaling boundaries.

---

## 6. Isolation Forest Parameters

Based on the global distribution profiling:
- **Total Rows:** 2,830,743
- **Benign:** 2,273,097 (80.3%)
- **Attack:** 557,646 (19.7%)

**Recommendation:**
- Set the Isolation Forest `contamination` parameter to **0.197** to align with the true global anomaly ratio.

---

## 7. Execution Architecture (Scikit-Learn)

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler, FunctionTransformer
from sklearn.impute import SimpleImputer
import numpy as np

# 1. Deduplicate & Drop Columns (Outside pipeline, on raw data)
# df = df.drop_duplicates(...)
# df = df.drop(columns=constant_and_redundant_cols)

# 2. Log Transform (Custom)
log_transformer = FunctionTransformer(np.log1p, validate=True)

# 3. Leak-free Pipeline
preprocessing_pipeline = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('log_transform', log_transformer),
    ('scaler', RobustScaler())
])

# Fit on X_train ONLY, then transform X_train and X_test
```
