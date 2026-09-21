# CICIDS2017 Final Preprocessing Pipeline Design

## 1. Executive Summary

This document specifies the complete, evidence-based, leakage-safe preprocessing pipeline for the CICIDS2017 Isolation Forest experiment. Every decision is supported by verified data evidence and is designed for scientific reproducibility.

**Dataset**: 2,830,743 rows × 77 numeric features + metadata
**Target**: Isolation Forest anomaly detection with supervised evaluation
**Key constraint**: All preprocessing parameters must be fitted on training data only

---

## 2. Complete Pipeline Specification

### STAGE 1: RAW DATA LOAD
- **Input**: `CICIDS2017_COMBINED_RAW.csv`
- **Operation**: `pd.read_csv()`
- **Output**: DataFrame (2,830,743 × 81)
- **Parameters learned**: None
- **Leakage risk**: None
- **Evidence**: Verified — 2,830,743 rows, 81 columns (77 features + Label + 3 metadata)

### STAGE 2: SCHEMA VALIDATION
- **Input**: Raw DataFrame
- **Operations**:
  1. Strip whitespace from column names: `df.columns = df.columns.str.strip()`
  2. Verify all expected features are present
  3. Verify `Fwd Header Length.1` (column 34) is absent (already removed during integration)
- **Output**: Validated DataFrame
- **Parameters learned**: None
- **Leakage risk**: None
- **Evidence**: SCHEMA_COMPATIBILITY_REPORT.md — 64/79 columns had leading whitespace, repaired during integration

### STAGE 3: LABEL ENCODING REPAIR
- **Input**: Validated DataFrame
- **Operation**: Sanitize Thursday Web Attack labels
  ```python
  label_mapping = {
      'Web Attack \ufffd Brute Force': 'Web Attack - Brute Force',
      'Web Attack \ufffd XSS': 'Web Attack - XSS',
      'Web Attack \ufffd Sql Injection': 'Web Attack - Sql Injection'
  }
  df['Label'] = df['Label'].replace(label_mapping).str.strip()
  ```
- **Output**: DataFrame with clean labels
- **Parameters learned**: None
- **Leakage risk**: None
- **Evidence**: Verified — Windows-1252 byte 0x96 produces U+FFFD replacement character in UTF-8

### STAGE 4: LABEL CONFLICT REMOVAL
- **Input**: DataFrame with clean labels
- **Operation**: Remove all rows where identical feature vectors have conflicting labels
  ```python
  feature_cols = [c for c in df.columns if c not in ['Label', 'Source_File', 'Source_Day', 'Source_Row_Index']]
  conflict_mask = df.duplicated(subset=feature_cols, keep=False)
  conflict_groups = df[conflict_mask].groupby(feature_cols)['Label'].nunique()
  conflict_features = conflict_groups[conflict_groups > 1].index
  conflict_row_mask = df.set_index(feature_cols).index.isin(conflict_features)
  df = df[~conflict_row_mask].copy()
  ```
- **Output**: DataFrame without label conflicts
- **Rows removed**: ~6,666 (0.24%)
- **Parameters learned**: None
- **Leakage risk**: None — removal is based on feature+label incompatibility, not data distribution
- **Evidence**: 697 conflicting feature vectors identified; primarily BENIGN vs PortScan (564), BENIGN vs DoS Hulk (129)

### STAGE 5: DEDUPLICATION
- **Input**: DataFrame without label conflicts
- **Operation**: Remove exact duplicate feature vectors
  ```python
  df = df.drop_duplicates(subset=feature_cols, keep='first')
  ```
- **Output**: DataFrame with unique feature vectors
- **Rows remaining**: ~2,521,664
- **Parameters learned**: None
- **Leakage risk**: None — occurs before train/test split
- **Evidence**: 309,079 duplicates (10.92%) verified; 111,795 inter-dataset, 196,278 intra-dataset

### STAGE 6: METADATA / LABEL ISOLATION
- **Input**: Clean DataFrame
- **Operation**: Separate metadata, labels, and features into distinct variables
  ```python
  metadata_cols = ['Source_File', 'Source_Day', 'Source_Row_Index']
  label_col = 'Label'
  feature_cols = [c for c in df.columns if c not in metadata_cols + [label_col]]
  
  X = df[feature_cols].copy()
  y = df[label_col].copy()
  metadata = df[metadata_cols].copy()
  ```
- **Output**: Feature matrix X, label vector y, metadata DataFrame
- **Parameters learned**: None
- **Leakage risk**: None
- **Critical constraint**: `Source_Day`, `Source_File`, `Label` must NEVER appear in model feature matrix

### STAGE 7: TRAIN / VALIDATION / TEST SPLIT
- **Input**: X, y, metadata
- **Operation**: Source-day based splitting (NO random splitting)
  ```python
  train_mask = metadata['Source_Day'] == 'Monday'
  val_mask = metadata['Source_Day'] == 'Tuesday'
  test_masks = {
      'Wednesday': metadata['Source_Day'] == 'Wednesday',
      'Thursday-Morning': metadata['Source_Day'] == 'Thursday-Morning',
      'Thursday-Afternoon': metadata['Source_Day'] == 'Thursday-Afternoon',
      'Friday-Morning': metadata['Source_Day'] == 'Friday-Morning',
      'Friday-PortScan': metadata['Source_Day'] == 'Friday-PortScan',
      'Friday-DDoS': metadata['Source_Day'] == 'Friday-DDoS',
  }
  
  X_train, y_train = X[train_mask], y[train_mask]
  X_val, y_val = X[val_mask], y[val_mask]
  X_test = {name: X[mask] for name, mask in test_masks.items()}
  y_test = {name: y[mask] for name, mask in test_masks.items()}
  ```
- **Output**: Train/Val/Test splits
- **Parameters learned**: None (split is by source day, not learned)
- **Leakage risk**: None — temporal separation prevents leakage
- **Evidence**: Source-Day analysis shows clean separation: Monday=0% attack, each other day has specific attack types

### STAGE 8: ZERO-DURATION / INF HANDLING (TRAIN-FITTED)
- **Input**: Train, Val, Test splits
- **Operation**: 
  ```python
  def handle_zero_duration(X):
      X = X.copy()
      # Step 1: Create flag BEFORE modification
      X['Is_Zero_Duration'] = (X['Flow Duration'] == 0).astype(int)
      
      # Step 2: Replace zero duration with 1 μs for rate computation
      X['Flow Duration'] = X['Flow Duration'].clip(lower=1.0)
      
      # Step 3: Recompute rate features deterministically
      # Note: Total Fwd Packets + Total Backward Packets = Total Packets
      total_packets = X['Total Fwd Packets'] + X['Total Backward Packets']
      total_bytes = X['Total Length of Fwd Packets'] + X['Total Length of Bwd Packets']
      
      # Only recompute where duration was zero (to preserve original values elsewhere)
      zero_dur_mask = X['Is_Zero_Duration'] == 1
      X.loc[zero_dur_mask, 'Flow Packets/s'] = total_packets[zero_dur_mask] / (X.loc[zero_dur_mask, 'Flow Duration'] * 1e-6)
      X.loc[zero_dur_mask, 'Flow Bytes/s'] = total_bytes[zero_dur_mask] / (X.loc[zero_dur_mask, 'Flow Duration'] * 1e-6)
      
      return X
  
  X_train = handle_zero_duration(X_train)
  X_val = handle_zero_duration(X_val)
  X_test = {name: handle_zero_duration(X) for name, X in X_test.items()}
  ```
- **Output**: All splits with zero-duration handled
- **Parameters learned**: None (deterministic rule, not learned from data)
- **Leakage risk**: None — deterministic transformation, no data-dependent parameters
- **Evidence**: 2,867 zero-duration flows verified; 100% co-occur with Inf; Is_Zero_Duration flag preserves semantic information

### STAGE 9: NaN HANDLING (TRAIN-FITTED)
- **Input**: All splits (after zero-duration handling)
- **Operation**: Since ALL NaN values are in Flow Bytes/s AND all overlap with zero-duration flows AND the zero-duration handling already recomputes Flow Bytes/s (= 0.0 when Total Bytes = 0), NaN values are already resolved by Stage 8.
  
  **Verification**: After Stage 8, confirm zero NaN values remain:
  ```python
  assert X_train.isna().sum().sum() == 0, "NaN should be resolved by zero-duration handling"
  ```
  
  **Fallback** (if any NaN remains): Median imputation fitted on training data only:
  ```python
  from sklearn.impute import SimpleImputer
  imputer = SimpleImputer(strategy='median')
  X_train_imputed = imputer.fit_transform(X_train)  # FIT ON TRAIN ONLY
  X_val_imputed = imputer.transform(X_val)
  X_test_imputed = {name: imputer.transform(X) for name, X in X_test.items()}
  ```
- **Output**: All splits NaN-free
- **Parameters learned**: Median values (if fallback needed) — fitted on training data only
- **Leakage risk**: LOW — if fallback is used, medians are from training data only
- **Evidence**: 1,358 NaN values all in Flow Bytes/s, all overlap with zero-duration, all resolved by Stage 8 recomputation

### STAGE 10: CONSTANT FEATURE REMOVAL
- **Input**: All splits
- **Operation**: Drop 8 constant-zero features
  ```python
  constant_features = [
      'Bwd PSH Flags', 'Bwd URG Flags',
      'Fwd Avg Bytes/Bulk', 'Fwd Avg Packets/Bulk', 'Fwd Avg Bulk Rate',
      'Bwd Avg Bytes/Bulk', 'Bwd Avg Packets/Bulk', 'Bwd Avg Bulk Rate'
  ]
  X_train = X_train.drop(columns=constant_features)
  X_val = X_val.drop(columns=constant_features)
  X_test = {name: X.drop(columns=constant_features) for name, X in X_test.items()}
  ```
- **Output**: All splits without constant features
- **Parameters learned**: None
- **Leakage risk**: None
- **Evidence**: 8 features verified constant zero across all 2.83M rows

### STAGE 11: REDUNDANT FEATURE REMOVAL
- **Input**: All splits
- **Operation**: Drop 10 redundant features (keeping canonical representatives)
  ```python
  redundant_features = [
      'Subflow Fwd Packets',    # Duplicate of Total Fwd Packets (r=1.0)
      'Subflow Bwd Packets',    # Duplicate of Total Backward Packets (r=1.0)
      'Subflow Fwd Bytes',      # Duplicate of Total Length of Fwd Packets (r=1.0)
      'Subflow Bwd Bytes',      # Duplicate of Total Length of Bwd Packets (r=1.0)
      'Avg Fwd Segment Size',   # Duplicate of Fwd Packet Length Mean (r=1.0)
      'Avg Bwd Segment Size',   # Duplicate of Bwd Packet Length Mean (r=1.0)
      'SYN Flag Count',         # Duplicate of Fwd PSH Flags (r=1.0)
      'CWE Flag Count',         # Duplicate of Fwd URG Flags (r=1.0)
      'Bwd Header Length',       # Near-duplicate of Fwd Header Length (r=0.999)
      'ECE Flag Count',         # Duplicate of RST Flag Count (r=1.0)
  ]
  X_train = X_train.drop(columns=redundant_features)
  X_val = X_val.drop(columns=redundant_features)
  X_test = {name: X.drop(columns=redundant_features) for name, X in X_test.items()}
  ```
- **Output**: All splits without redundant features
- **Parameters learned**: None
- **Leakage risk**: None
- **Evidence**: 10 features verified as r ≥ 0.999 duplicates; canonical representatives chosen by interpretability
- **Remaining features**: 77 - 8 (constant) - 10 (redundant) + 1 (Is_Zero_Duration) = **60 features** (with Destination Port) or **59 features** (without Destination Port, E1)

### STAGE 12: FEATURE TRANSFORMATION
- **Input**: All splits (60 features with port, 59 without)
- **Operation**: Apply signed-log transformation to heavy-tailed features with negative values; log1p to non-negative heavy-tailed features.

  **CRITICAL FINDING**: 12 features contain negative values. Standard `np.log1p(x)` is undefined for x < -1. The original proposal to apply `log10(x+1)` to all heavy-tailed features is INVALID for these features.

  **Corrected transformation strategy**:

  ```python
  # Features safe for log1p (non-negative, heavy-tailed)
  log1p_features = [
      'Total Fwd Packets', 'Total Backward Packets',
      'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
      'Flow IAT Std', 'Fwd IAT Total', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max',
      'Bwd IAT Total', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max',
      'Fwd Packets/s', 'Bwd Packets/s',
      'Active Mean', 'Active Std', 'Active Max', 'Active Min',
      'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min',
      'act_data_pkt_fwd'
  ]
  
  # Features requiring signed transformation (have negative values)
  # Use: sign(x) * log1p(abs(x)) for features with both positive and negative values
  signed_log_features = [
      'Flow Duration', 'Flow Bytes/s', 'Flow Packets/s',
      'Flow IAT Mean', 'Flow IAT Max', 'Flow IAT Min',
      'Fwd IAT Min',
      'Fwd Header Length', 'Bwd Header Length', 'min_seg_size_forward',
      'Init_Win_bytes_forward', 'Init_Win_bytes_backward'
  ]
  
  def signed_log_transform(x):
      """Transform: sign(x) * log1p(|x|)"""
      return np.sign(x) * np.log1p(np.abs(x))
  
  # Apply transformations
  for col in log1p_features:
      if col in X_train.columns:
          X_train[col] = np.log1p(X_train[col])
          X_val[col] = np.log1p(X_val[col])
          X_test = {name: X.assign(**{col: np.log1p(X[col])}) for name, X in X_test.items()}
  
  for col in signed_log_features:
      if col in X_train.columns:
          X_train[col] = signed_log_transform(X_train[col])
          X_val[col] = signed_log_transform(X_val[col])
          X_test = {name: X.assign(**{col: signed_log_transform(X[col])}) for name, X in X_test.items()}
  ```

- **Output**: All splits with transformed features
- **Parameters learned**: None (deterministic mathematical function)
- **Leakage risk**: None — no data-dependent parameters
- **Evidence**: 12 features with negative values verified; log1p is mathematically undefined for x < -1

### STAGE 13: OPTIONAL SCALING
- **Input**: Transformed splits
- **Operation**: RobustScaler fitted on training data only
  ```python
  from sklearn.preprocessing import RobustScaler
  scaler = RobustScaler()
  X_train_scaled = scaler.fit_transform(X_train)  # FIT ON TRAIN ONLY
  X_val_scaled = scaler.transform(X_val)
  X_test_scaled = {name: scaler.transform(X) for name, X in X_test.items()}
  ```
- **Output**: Scaled feature matrices
- **Parameters learned**: Median and IQR — fitted on training data only
- **Leakage risk**: LOW if fitted on training data only
- **Evidence**: Scaling is not required for tree-based Isolation Forest but improves consistency for future supervised models
- **Note**: This stage is **OPTIONAL** for Isolation Forest. Include for pipeline consistency if supervised models will use the same preprocessing.

### STAGE 14: FINAL FEATURE MATRIX
- **Input**: Preprocessed splits
- **Output**: 
  - `X_train`: ~502,983 rows × 61 features (60 + Is_Zero_Duration)
  - `X_val`: ~421,844 rows × 61 features
  - `X_test[name]`: Variable sizes × 61 features
- **Feature whitelist** (61 features):
  ```
  Destination Port*, Flow Duration, Total Fwd Packets, Total Backward Packets,
  Total Length of Fwd Packets, Total Length of Bwd Packets, Fwd Packet Length Max,
  Fwd Packet Length Min, Fwd Packet Length Mean, Fwd Packet Length Std,
  Bwd Packet Length Max, Bwd Packet Length Min, Bwd Packet Length Mean,
  Bwd Packet Length Std, Flow Bytes/s, Flow Packets/s, Flow IAT Mean,
  Flow IAT Std, Flow IAT Max, Flow IAT Min, Fwd IAT Total, Fwd IAT Mean,
  Fwd IAT Std, Fwd IAT Max, Fwd IAT Min, Bwd IAT Total, Bwd IAT Mean,
  Bwd IAT Std, Bwd IAT Max, Bwd IAT Min, Fwd PSH Flags, Fwd URG Flags,
  Fwd Header Length, Fwd Packets/s, Bwd Packets/s, Min Packet Length,
  Max Packet Length, Packet Length Mean, Packet Length Std,
  Packet Length Variance, FIN Flag Count, RST Flag Count, PSH Flag Count,
  ACK Flag Count, URG Flag Count, Down/Up Ratio, Average Packet Size,
  Init_Win_bytes_forward, Init_Win_bytes_backward, act_data_pkt_fwd,
  min_seg_size_forward, Active Mean, Active Std, Active Max, Active Min,
  Idle Mean, Idle Std, Idle Max, Idle Min, Is_Zero_Duration
  ```
  *Destination Port is experimental — included in primary model, ablated in secondary model.

### STAGE 15: ISOLATION FOREST TRAINING
- **Input**: X_train (Monday BENIGN, 61 features)
- **Operation**: 
  ```python
  from sklearn.ensemble import IsolationForest
  
  iso_forest = IsolationForest(
      n_estimators=100,
      max_samples=256,
      contamination=0.01,  # Experimental — tune on validation
      max_features=1.0,
      bootstrap=False,
      random_state=42,
      n_jobs=-1
  )
  iso_forest.fit(X_train)
  ```
- **Output**: Trained Isolation Forest model
- **Parameters learned**: Tree structure — fitted on training data only
- **Leakage risk**: None — model trained on Monday BENIGN only

---

## 3. Pipeline Summary Table

| Stage | Operation | Input | Output | Parameters Learned | Leakage Risk |
|:---|:---|:---|:---|:---|:---|
| 1 | Load CSV | File | DataFrame | None | None |
| 2 | Schema validation | DataFrame | Validated DF | None | None |
| 3 | Label repair | Validated DF | Clean labels | None | None |
| 4 | Conflict removal | DF | DF - 6,666 rows | None | None |
| 5 | Deduplication | DF | DF - ~309K rows | None | None |
| 6 | Metadata isolation | DF | X, y, metadata | None | None |
| 7 | Day-based split | X, y | Train/Val/Test | None | None |
| 8 | Zero-duration handling | All splits | Modified rates + flag | None | None |
| 9 | NaN handling | All splits | NaN-free | Median (train only) | Low |
| 10 | Constant removal | All splits | -8 features | None | None |
| 11 | Redundant removal | All splits | -10 features | None | None |
| 12 | Feature transformation | All splits | Transformed | None | None |
| 13 | Optional scaling | All splits | Scaled | Median, IQR (train) | Low |
| 14 | Final matrix | All splits | 61-feature X | None | None |
| 15 | Isolation Forest | X_train | Model | Tree structure (train) | None |

---

## 4. Reproducibility Checklist

- [ ] Random seed: `random_state=42` for Isolation Forest
- [ ] Preprocessing parameters saved as JSON (medians, scaler params)
- [ ] Feature whitelist saved as list
- [ ] Training logs include all hyperparameters
- [ ] Model saved as joblib/pickle
- [ ] Results logged to structured file
