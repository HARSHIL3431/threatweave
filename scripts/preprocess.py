"""
CICIDS2017 Leakage-Safe Preprocessing Pipeline

Implements the audited 15-stage pipeline for Isolation Forest anomaly detection.
All decisions documented in demo/reports/PREPROCESSING_DECISION_MATRIX.md.

Usage:
    from preprocess import CICIDS2017Preprocessor
    
    preprocessor = CICIDS2017Preprocessor(data_path="data/combined/CICIDS2017_COMBINED_RAW.csv")
    splits = preprocessor.run()
    # splits = {'X_train', 'y_train', 'X_val', 'y_val', 'X_test', 'y_test', 'metadata', 'feature_names'}
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any

warnings.filterwarnings('ignore')

# ============================================================
# CONSTANTS
# ============================================================

RANDOM_SEED = 42

METADATA_COLS = ['Source_File', 'Source_Day', 'Source_Row_Index']
LABEL_COL = 'Label'

# Stage 10: Constant features (zero variance across all 2.83M rows)
CONSTANT_FEATURES = [
    'Bwd PSH Flags', 'Bwd URG Flags',
    'Fwd Avg Bytes/Bulk', 'Fwd Avg Packets/Bulk', 'Fwd Avg Bulk Rate',
    'Bwd Avg Bytes/Bulk', 'Bwd Avg Packets/Bulk', 'Bwd Avg Bulk Rate'
]

# Stage 11: Redundant features (r >= 0.999 with canonical representative)
REDUNDANT_FEATURES = [
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

# Stage 12: Features safe for standard log1p (non-negative, heavy-tailed)
LOG1P_FEATURES = [
    'Total Fwd Packets', 'Total Backward Packets',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Flow IAT Std', 'Fwd IAT Total', 'Fwd IAT Mean', 'Fwd IAT Std', 'Fwd IAT Max',
    'Bwd IAT Total', 'Bwd IAT Mean', 'Bwd IAT Std', 'Bwd IAT Max',
    'Fwd Packets/s', 'Bwd Packets/s',
    'Active Mean', 'Active Std', 'Active Max', 'Active Min',
    'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min',
    'act_data_pkt_fwd'
]

# Stage 12: Features requiring signed transformation (have negative values)
# NOTE: Bwd Header Length is NOT here because it's removed in Stage 11
SIGNED_LOG_FEATURES = [
    'Flow Duration', 'Flow Bytes/s', 'Flow Packets/s',
    'Flow IAT Mean', 'Flow IAT Max', 'Flow IAT Min',
    'Fwd IAT Min',
    'Fwd Header Length', 'min_seg_size_forward',
    'Init_Win_bytes_forward', 'Init_Win_bytes_backward'
]

# Source-day split mapping
TRAIN_DAY = 'Monday'
VAL_DAY = 'Tuesday'
TEST_DAYS = [
    'Wednesday', 'Thursday-Morning', 'Thursday-Afternoon',
    'Friday-Morning', 'Friday-PortScan', 'Friday-DDoS'
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def signed_log_transform(x: pd.Series) -> pd.Series:
    """Signed log transformation: sign(x) * log1p(|x|)
    
    Mathematically valid for all real numbers including negatives.
    Preserves sign while compressing heavy tails.
    """
    return np.sign(x) * np.log1p(np.abs(x))


def handle_zero_duration(X: pd.DataFrame) -> pd.DataFrame:
    """Handle zero-duration flows that cause Inf/NaN in rate features.
    
    Creates Is_Zero_Duration flag, clips Duration to 1us minimum,
    and recomputes Flow Packets/s and Flow Bytes/s deterministically.
    
    Evidence: 2,867 zero-duration flows; 62% benign; 100% cause Inf.
    """
    X = X.copy()
    
    # Step 1: Create flag BEFORE modification
    X['Is_Zero_Duration'] = (X['Flow Duration'] == 0).astype(int)
    
    # Step 2: Replace zero duration with 1 us for rate computation
    X['Flow Duration'] = X['Flow Duration'].clip(lower=1.0)
    
    # Step 3: Recompute rate features only where duration was zero
    total_packets = X['Total Fwd Packets'] + X['Total Backward Packets']
    total_bytes = X['Total Length of Fwd Packets'] + X['Total Length of Bwd Packets']
    
    zero_dur_mask = X['Is_Zero_Duration'] == 1
    X.loc[zero_dur_mask, 'Flow Packets/s'] = (
        total_packets[zero_dur_mask] / (X.loc[zero_dur_mask, 'Flow Duration'] * 1e-6)
    )
    X.loc[zero_dur_mask, 'Flow Bytes/s'] = (
        total_bytes[zero_dur_mask] / (X.loc[zero_dur_mask, 'Flow Duration'] * 1e-6)
    )
    
    return X


# ============================================================
# MAIN PREPROCESSOR CLASS
# ============================================================

class CICIDS2017Preprocessor:
    """Leakage-safe preprocessing pipeline for CICIDS2017.
    
    All parameters are either:
    - Deterministic constants (no learning)
    - Fitted on training data only (no test leakage)
    
    Pipeline stages:
    1. Load CSV
    2. Schema validation
    3. Label encoding repair
    4. Label conflict removal
    5. Deduplication
    6. Metadata/label isolation
    7. Source-day based split
    8. Zero-duration handling
    9. NaN verification
    10. Constant feature removal
    11. Redundant feature removal
    12. Feature transformation
    13. Optional scaling (disabled by default for IF)
    14. Final feature matrix
    """
    
    def __init__(
        self,
        data_path: str = "data/combined/CICIDS2017_COMBINED_RAW.csv",
        apply_scaling: bool = False,
        include_destination_port: bool = True,
        verbose: bool = True
    ):
        self.data_path = data_path
        self.apply_scaling = apply_scaling
        self.include_destination_port = include_destination_port
        self.verbose = verbose
        
        # Fitted parameters (set during fit on training data)
        self.scaler = None
        self.feature_names = None
        self.removed_features = None
        
        # Pipeline state
        self.raw_df = None
        self.splits = None
    
    def _log(self, msg: str):
        if self.verbose:
            print(f"  {msg}")
    
    # --------------------------------------------------------
    # Stage 1: Load CSV
    # --------------------------------------------------------
    def _load(self) -> pd.DataFrame:
        self._log("[Stage 1] Loading CSV...")
        df = pd.read_csv(self.data_path, low_memory=False)
        self._log(f"  Shape: {df.shape}")
        return df
    
    # --------------------------------------------------------
    # Stage 2: Schema Validation
    # --------------------------------------------------------
    def _validate_schema(self, df: pd.DataFrame) -> pd.DataFrame:
        self._log("[Stage 2] Schema validation...")
        df.columns = df.columns.str.strip()
        
        expected_cols = [LABEL_COL] + METADATA_COLS
        missing = [c for c in expected_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing expected columns: {missing}")
        
        self._log(f"  Columns after strip: {len(df.columns)}")
        return df
    
    # --------------------------------------------------------
    # Stage 3: Label Encoding Repair
    # --------------------------------------------------------
    def _repair_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        self._log("[Stage 3] Label encoding repair...")
        label_mapping = {
            'Web Attack \ufffd Brute Force': 'Web Attack - Brute Force',
            'Web Attack \ufffd XSS': 'Web Attack - XSS',
            'Web Attack \ufffd Sql Injection': 'Web Attack - Sql Injection'
        }
        df[LABEL_COL] = df[LABEL_COL].replace(label_mapping).str.strip()
        n_labels = df[LABEL_COL].nunique()
        self._log(f"  Unique labels: {n_labels}")
        return df
    
    # --------------------------------------------------------
    # Stage 4: Label Conflict Removal
    # --------------------------------------------------------
    def _remove_label_conflicts(self, df: pd.DataFrame) -> pd.DataFrame:
        self._log("[Stage 4] Label conflict removal...")
        feature_cols = [c for c in df.columns if c not in METADATA_COLS + [LABEL_COL]]
        
        conflict_mask = df.duplicated(subset=feature_cols, keep=False)
        conflict_groups = df[conflict_mask].groupby(feature_cols)[LABEL_COL].nunique()
        conflict_features = conflict_groups[conflict_groups > 1].index
        
        conflict_row_mask = df.set_index(feature_cols).index.isin(conflict_features)
        n_removed = conflict_row_mask.sum()
        df = df[~conflict_row_mask].copy()
        
        self._log(f"  Conflicting feature vectors: {len(conflict_features)}")
        self._log(f"  Rows removed: {n_removed:,}")
        self._log(f"  Rows remaining: {len(df):,}")
        return df
    
    # --------------------------------------------------------
    # Stage 5: Deduplication
    # --------------------------------------------------------
    def _deduplicate(self, df: pd.DataFrame) -> pd.DataFrame:
        self._log("[Stage 5] Deduplication...")
        feature_cols = [c for c in df.columns if c not in METADATA_COLS + [LABEL_COL]]
        
        n_before = len(df)
        df = df.drop_duplicates(subset=feature_cols, keep='first')
        n_removed = n_before - len(df)
        
        self._log(f"  Rows removed: {n_removed:,}")
        self._log(f"  Rows remaining: {len(df):,}")
        return df
    
    # --------------------------------------------------------
    # Stage 6: Metadata / Label Isolation
    # --------------------------------------------------------
    def _isolate_metadata(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        self._log("[Stage 6] Metadata/label isolation...")
        feature_cols = [c for c in df.columns if c not in METADATA_COLS + [LABEL_COL]]
        
        X = df[feature_cols].copy()
        y = df[LABEL_COL].copy()
        metadata = df[METADATA_COLS].copy()
        
        self._log(f"  Feature matrix: {X.shape}")
        self._log(f"  Features: {list(X.columns)}")
        
        # Critical verification
        for col in METADATA_COLS + [LABEL_COL]:
            assert col not in X.columns, f"LEAKAGE: {col} found in feature matrix!"
        
        return X, y, metadata
    
    # --------------------------------------------------------
    # Stage 7: Source-Day Based Split
    # --------------------------------------------------------
    def _split_by_day(
        self, X: pd.DataFrame, y: pd.Series, metadata: pd.DataFrame
    ) -> Dict[str, Any]:
        self._log("[Stage 7] Source-day based splitting...")
        
        train_mask = metadata['Source_Day'] == TRAIN_DAY
        val_mask = metadata['Source_Day'] == VAL_DAY
        test_masks = {day: metadata['Source_Day'] == day for day in TEST_DAYS}
        
        splits = {
            'X_train': X[train_mask].copy(),
            'y_train': y[train_mask].copy(),
            'X_val': X[val_mask].copy(),
            'y_val': y[val_mask].copy(),
            'X_test': {day: X[mask].copy() for day, mask in test_masks.items()},
            'y_test': {day: y[mask].copy() for day, mask in test_masks.items()},
        }
        
        self._log(f"  Train (Monday): {splits['X_train'].shape[0]:,} rows")
        self._log(f"  Val (Tuesday):  {splits['X_val'].shape[0]:,} rows")
        for day, X_test in splits['X_test'].items():
            self._log(f"  Test ({day}): {X_test.shape[0]:,} rows")
        
        # Verify train is 100% benign
        train_labels = splits['y_train'].unique()
        assert len(train_labels) == 1 and train_labels[0] == 'BENIGN', \
            f"Training set is not 100% BENIGN! Labels: {train_labels}"
        
        return splits
    
    # --------------------------------------------------------
    # Stage 8: Zero-Duration Handling
    # --------------------------------------------------------
    def _handle_zero_duration(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[Stage 8] Zero-duration handling...")
        
        splits['X_train'] = handle_zero_duration(splits['X_train'])
        splits['X_val'] = handle_zero_duration(splits['X_val'])
        splits['X_test'] = {
            day: handle_zero_duration(X) for day, X in splits['X_test'].items()
        }
        
        # Verify no Inf remains
        for split_name, X in [('train', splits['X_train']), ('val', splits['X_val'])]:
            inf_count = np.isinf(X.select_dtypes(include=[np.number])).sum().sum()
            self._log(f"  {split_name} Inf count after handling: {inf_count}")
        
        return splits
    
    # --------------------------------------------------------
    # Stage 9: NaN Verification
    # --------------------------------------------------------
    def _verify_nan(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[Stage 9] NaN verification...")
        
        train_nan = splits['X_train'].isna().sum().sum()
        self._log(f"  Train NaN count: {train_nan}")
        
        if train_nan > 0:
            self._log("  WARNING: NaN values remain. Applying median imputation (train-fitted)...")
            from sklearn.impute import SimpleImputer
            self.imputer = SimpleImputer(strategy='median')
            
            feature_names = splits['X_train'].columns.tolist()
            splits['X_train'] = pd.DataFrame(
                self.imputer.fit_transform(splits['X_train']),
                columns=feature_names, index=splits['X_train'].index
            )
            splits['X_val'] = pd.DataFrame(
                self.imputer.transform(splits['X_val']),
                columns=feature_names, index=splits['X_val'].index
            )
            splits['X_test'] = {
                day: pd.DataFrame(
                    self.imputer.transform(X),
                    columns=feature_names, index=X.index
                ) for day, X in splits['X_test'].items()
            }
        else:
            self._log("  No NaN values. No imputation needed.")
        
        return splits
    
    # --------------------------------------------------------
    # Stage 10: Constant Feature Removal
    # --------------------------------------------------------
    def _remove_constants(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[Stage 10] Constant feature removal...")
        
        features_to_drop = [f for f in CONSTANT_FEATURES if f in splits['X_train'].columns]
        
        splits['X_train'] = splits['X_train'].drop(columns=features_to_drop)
        splits['X_val'] = splits['X_val'].drop(columns=features_to_drop)
        splits['X_test'] = {
            day: X.drop(columns=features_to_drop) for day, X in splits['X_test'].items()
        }
        
        self._log(f"  Removed {len(features_to_drop)} constant features")
        self._log(f"  Features remaining: {splits['X_train'].shape[1]}")
        return splits
    
    # --------------------------------------------------------
    # Stage 11: Redundant Feature Removal
    # --------------------------------------------------------
    def _remove_redundants(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[Stage 11] Redundant feature removal...")
        
        features_to_drop = [f for f in REDUNDANT_FEATURES if f in splits['X_train'].columns]
        
        splits['X_train'] = splits['X_train'].drop(columns=features_to_drop)
        splits['X_val'] = splits['X_val'].drop(columns=features_to_drop)
        splits['X_test'] = {
            day: X.drop(columns=features_to_drop) for day, X in splits['X_test'].items()
        }
        
        self._log(f"  Removed {len(features_to_drop)} redundant features")
        self._log(f"  Features remaining: {splits['X_train'].shape[1]}")
        return splits
    
    # --------------------------------------------------------
    # Stage 12: Feature Transformation
    # --------------------------------------------------------
    def _transform_features(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[Stage 12] Feature transformation...")
        
        train_cols = set(splits['X_train'].columns)
        
        # log1p for non-negative heavy-tailed features
        log1p_to_apply = [f for f in LOG1P_FEATURES if f in train_cols]
        self._log(f"  log1p features: {len(log1p_to_apply)}")
        
        for col in log1p_to_apply:
            splits['X_train'][col] = np.log1p(splits['X_train'][col])
            splits['X_val'][col] = np.log1p(splits['X_val'][col])
            splits['X_test'] = {
                day: X.assign(**{col: np.log1p(X[col])}) 
                for day, X in splits['X_test'].items()
            }
        
        # Signed log for features with negative values
        signed_to_apply = [f for f in SIGNED_LOG_FEATURES if f in train_cols]
        self._log(f"  signed-log features: {len(signed_to_apply)}")
        
        for col in signed_to_apply:
            splits['X_train'][col] = signed_log_transform(splits['X_train'][col])
            splits['X_val'][col] = signed_log_transform(splits['X_val'][col])
            splits['X_test'] = {
                day: X.assign(**{col: signed_log_transform(X[col])})
                for day, X in splits['X_test'].items()
            }
        
        # Verify no NaN/Inf after transformation
        for split_name, X in [('train', splits['X_train']), ('val', splits['X_val'])]:
            nan_after = X.isna().sum().sum()
            inf_after = np.isinf(X.select_dtypes(include=[np.number])).sum().sum()
            self._log(f"  {split_name} after transform - NaN: {nan_after}, Inf: {inf_after}")
        
        return splits
    
    # --------------------------------------------------------
    # Stage 13: Optional Scaling
    # --------------------------------------------------------
    def _scale_features(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        if not self.apply_scaling:
            self._log("[Stage 13] Scaling disabled (Isolation Forest is tree-based)")
            return splits
        
        self._log("[Stage 13] RobustScaler (fit on train only)...")
        from sklearn.preprocessing import RobustScaler
        
        self.scaler = RobustScaler()
        feature_names = splits['X_train'].columns.tolist()
        
        splits['X_train'] = pd.DataFrame(
            self.scaler.fit_transform(splits['X_train']),
            columns=feature_names, index=splits['X_train'].index
        )
        splits['X_val'] = pd.DataFrame(
            self.scaler.transform(splits['X_val']),
            columns=feature_names, index=splits['X_val'].index
        )
        splits['X_test'] = {
            day: pd.DataFrame(
                self.scaler.transform(X),
                columns=feature_names, index=X.index
            ) for day, X in splits['X_test'].items()
        }
        
        self._log(f"  Scaler fitted on {splits['X_train'].shape[0]:,} training rows")
        return splits
    
    # --------------------------------------------------------
    # Stage 14: Final Feature Matrix
    # --------------------------------------------------------
    def _finalize(self, splits: Dict[str, Any]) -> Dict[str, Any]:
        self._log("[Stage 14] Finalizing feature matrix...")
        
        self.feature_names = splits['X_train'].columns.tolist()
        self.removed_features = [
            f for f in CONSTANT_FEATURES + REDUNDANT_FEATURES
            if f not in self.feature_names
        ]
        
        self._log(f"  Final feature count: {len(self.feature_names)}")
        self._log(f"  Features: {self.feature_names}")
        
        # Critical leakage verification
        forbidden = set(METADATA_COLS + [LABEL_COL])
        for name in self.feature_names:
            assert name not in forbidden, f"LEAKAGE: {name} is in feature matrix!"
        
        # Verify column order is identical across all splits
        for day, X_test in splits['X_test'].items():
            assert list(X_test.columns) == self.feature_names, \
                f"Column mismatch in test split {day}!"
        
        splits['feature_names'] = self.feature_names
        return splits
    
    # --------------------------------------------------------
    # Main Pipeline
    # --------------------------------------------------------
    def run(self) -> Dict[str, Any]:
        """Execute the complete preprocessing pipeline.
        
        Returns:
            Dictionary with keys:
            - X_train, y_train: Training data (Monday BENIGN)
            - X_val, y_val: Validation data (Tuesday)
            - X_test: dict of {day: DataFrame} for test sets
            - y_test: dict of {day: Series} for test labels
            - feature_names: list of final feature names
            - metadata: original metadata for all rows
        """
        self._log("=" * 60)
        self._log("CICIDS2017 PREPROCESSING PIPELINE")
        self._log("=" * 60)
        
        # Stages 1-6: Load, validate, clean, split
        df = self._load()
        df = self._validate_schema(df)
        df = self._repair_labels(df)
        
        # Destination Port ablation (BEFORE conflict/dedup so feature vectors match final model features)
        if not self.include_destination_port and 'Destination Port' in df.columns:
            self._log("[Stage 3.5] Removing Destination Port (ablation)...")
            df = df.drop(columns=['Destination Port'])
            self._log(f"  Columns after port removal: {df.shape[1]}")
        
        df = self._remove_label_conflicts(df)
        df = self._deduplicate(df)
        X, y, metadata = self._isolate_metadata(df)
        
        # Stage 7: Split
        splits = self._split_by_day(X, y, metadata)
        
        # Stages 8-13: Transform
        splits = self._handle_zero_duration(splits)
        splits = self._verify_nan(splits)
        splits = self._remove_constants(splits)
        splits = self._remove_redundants(splits)
        splits = self._transform_features(splits)
        splits = self._scale_features(splits)
        
        # Stage 14: Finalize
        splits = self._finalize(splits)
        
        self._log("=" * 60)
        self._log("PIPELINE COMPLETE")
        self._log("=" * 60)
        
        self.splits = splits
        return splits
    
    def save_config(self, output_path: str = "data/processed/preprocessing_config.json"):
        """Save preprocessing configuration for reproducibility."""
        config = {
            'data_path': self.data_path,
            'apply_scaling': self.apply_scaling,
            'include_destination_port': self.include_destination_port,
            'random_seed': RANDOM_SEED,
            'constant_features_removed': CONSTANT_FEATURES,
            'redundant_features_removed': REDUNDANT_FEATURES,
            'log1p_features': [f for f in LOG1P_FEATURES if f in (self.feature_names or [])],
            'signed_log_features': [f for f in SIGNED_LOG_FEATURES if f in (self.feature_names or [])],
            'feature_names': self.feature_names,
            'train_day': TRAIN_DAY,
            'val_day': VAL_DAY,
            'test_days': TEST_DAYS,
        }
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        self._log(f"Config saved to {output_path}")


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="CICIDS2017 Preprocessing Pipeline")
    parser.add_argument("--data", default="data/combined/CICIDS2017_COMBINED_RAW.csv",
                        help="Path to combined CSV")
    parser.add_argument("--scaling", action="store_true",
                        help="Apply RobustScaler (optional for IF)")
    parser.add_argument("--no-port", action="store_true",
                        help="Exclude Destination Port from features")
    parser.add_argument("--output-dir", default="data/processed",
                        help="Output directory for processed data")
    args = parser.parse_args()
    
    preprocessor = CICIDS2017Preprocessor(
        data_path=args.data,
        apply_scaling=args.scaling,
        include_destination_port=not args.no_port,
    )
    
    splits = preprocessor.run()
    
    # Save processed splits
    os.makedirs(args.output_dir, exist_ok=True)
    
    splits['X_train'].to_csv(f"{args.output_dir}/X_train.csv", index=False)
    splits['y_train'].to_csv(f"{args.output_dir}/y_train.csv", index=False)
    splits['X_val'].to_csv(f"{args.output_dir}/X_val.csv", index=False)
    splits['y_val'].to_csv(f"{args.output_dir}/y_val.csv", index=False)
    
    for day, X_test in splits['X_test'].items():
        safe_name = day.replace('-', '_')
        X_test.to_csv(f"{args.output_dir}/X_test_{safe_name}.csv", index=False)
        splits['y_test'][day].to_csv(f"{args.output_dir}/y_test_{safe_name}.csv", index=False)
    
    preprocessor.save_config(f"{args.output_dir}/preprocessing_config.json")
    
    print(f"\nProcessed data saved to {args.output_dir}/")
