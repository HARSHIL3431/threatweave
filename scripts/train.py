"""
CICIDS2017 Isolation Forest Training

Trains Isolation Forest on Monday BENIGN traffic and scores all test sets.
All contamination values are experimental — not hard-coded.

Usage:
    from train import IsolationForestTrainer
    
    trainer = IsolationForestTrainer()
    results = trainer.train_and_score(splits)
"""

import numpy as np
import pandas as pd
import json
import os
import time
from typing import Dict, Any, Optional, List
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, average_precision_score,
    precision_recall_curve
)

RANDOM_SEED = 42

# Default hyperparameters
DEFAULT_PARAMS = {
    'n_estimators': 100,
    'max_samples': 256,
    'max_features': 1.0,
    'bootstrap': False,
    'random_state': RANDOM_SEED,
    'n_jobs': -1,
    'verbose': 0,
}

# Contamination values to experiment with
CONTAMINATION_GRID = [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]


class IsolationForestTrainer:
    """Trains Isolation Forest and evaluates across test sets.
    
    Training population: Monday BENIGN only (100% clean).
    Validation: Tuesday (for contamination tuning).
    Test: Wednesday through Friday (6 separate test sets).
    """
    
    def __init__(self, contamination: float = 0.01, params: Optional[Dict] = None):
        self.contamination = contamination
        self.params = {**DEFAULT_PARAMS, **(params or {})}
        self.params['contamination'] = contamination
        self.model = None
        self.train_time = None
        self.train_samples = None
    
    def train(self, X_train: pd.DataFrame) -> IsolationForest:
        """Train Isolation Forest on training data (Monday BENIGN).
        
        Args:
            X_train: Training feature matrix (Monday BENIGN, ~500K rows)
        
        Returns:
            Fitted IsolationForest model
        """
        print(f"Training Isolation Forest...")
        print(f"  Training samples: {X_train.shape[0]:,}")
        print(f"  Features: {X_train.shape[1]}")
        print(f"  Parameters: {self.params}")
        
        self.train_samples = X_train.shape[0]
        
        start_time = time.time()
        self.model = IsolationForest(**self.params)
        self.model.fit(X_train.values)
        self.train_time = time.time() - start_time
        
        print(f"  Training time: {self.train_time:.1f}s")
        return self.model
    
    def score(self, X: pd.DataFrame) -> np.ndarray:
        """Get anomaly scores for data (lower = more anomalous).
        
        Args:
            X: Feature matrix to score
        
        Returns:
            Array of anomaly scores
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")
        
        # score_samples returns negative scores (lower = more anomalous)
        # We negate so that higher = more anomalous for easier interpretation
        scores = -self.model.score_samples(X.values)
        return scores
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Get binary predictions (-1 = anomaly, 1 = normal).
        
        Args:
            X: Feature matrix to predict
        
        Returns:
            Array of predictions (-1 or 1)
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")
        
        return self.model.predict(X.values)
    
    def evaluate_split(
        self, X_test: pd.DataFrame, y_test: pd.Series, 
        split_name: str, threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Evaluate model on a single test split.
        
        Args:
            X_test: Test feature matrix
            y_test: Test labels
            split_name: Name of the split (e.g., "Wednesday")
            threshold: Optional custom threshold. If None, uses model's built-in threshold.
        
        Returns:
            Dictionary of evaluation metrics
        """
        scores = self.score(X_test)
        
        if threshold is not None:
            # Custom threshold: scores >= threshold -> anomaly
            predictions = (scores >= threshold).astype(int)
        else:
            # Use model's built-in prediction (-1/1 -> 0/1)
            predictions = (self.predict(X_test) == -1).astype(int)
        
        # Convert labels to binary (0=benign, 1=attack)
        y_binary = (y_test != 'BENIGN').astype(int).values
        
        # Basic metrics
        precision = precision_score(y_binary, predictions, zero_division=0)
        recall = recall_score(y_binary, predictions, zero_division=0)
        f1 = f1_score(y_binary, predictions, zero_division=0)
        
        # Confusion matrix
        tn, fp, fn, tp = confusion_matrix(y_binary, predictions).ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        
        # Anomaly-score-based metrics
        try:
            pr_auc = average_precision_score(y_binary, scores)
        except ValueError:
            pr_auc = 0.0
        
        try:
            roc_auc = roc_auc_score(y_binary, scores)
        except ValueError:
            roc_auc = 0.0
        
        # Per-class attack breakdown (counts enable offline F1/precision per class)
        attack_classes = y_test[y_test != 'BENIGN'].unique()
        attack_recall = {}
        attack_precision = {}
        attack_counts = {}
        for attack in attack_classes:
            attack_mask = (y_test == attack).values
            n_class = int(attack_mask.sum())
            class_tp = int(((predictions == 1) & attack_mask).sum())
            class_fn = n_class - class_tp
            attack_recall[attack] = float(class_tp / n_class) if n_class > 0 else 0.0
            attack_precision[attack] = float(class_tp / predictions.sum()) if predictions.sum() > 0 else 0.0
            attack_counts[attack] = {
                'samples': n_class,
                'tp': class_tp,
                'fn': class_fn,
                'recall': attack_recall[attack],
            }
        
        result = {
            'split_name': split_name,
            'total_samples': len(y_test),
            'attack_samples': int(y_binary.sum()),
            'benign_samples': int((y_binary == 0).sum()),
            'attack_ratio': float(y_binary.mean()),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'fpr': float(fpr),
            'pr_auc': float(pr_auc),
            'roc_auc': float(roc_auc),
            'tp': int(tp),
            'fp': int(fp),
            'fn': int(fn),
            'tn': int(tn),
            'threshold_used': float(threshold) if threshold is not None else 'model_default',
            'contamination': self.contamination,
            'attack_recall': attack_recall,
            'attack_precision': attack_precision,
            'attack_counts': attack_counts,
        }
        
        return result
    
    def evaluate_all(
        self, splits: Dict[str, Any], 
        thresholds: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Evaluate on all test sets.
        
        Args:
            splits: Output from CICIDS2017Preprocessor.run()
            thresholds: Optional per-split thresholds from validation tuning
        
        Returns:
            Dictionary with results for each test split
        """
        results = {}
        
        for day, X_test in splits['X_test'].items():
            y_test = splits['y_test'][day]
            threshold = thresholds.get(day) if thresholds else None
            result = self.evaluate_split(X_test, y_test, day, threshold)
            results[day] = result
            
            print(f"\n  {day}:")
            print(f"    Samples: {result['total_samples']:,} (attack: {result['attack_samples']:,})")
            print(f"    Precision: {result['precision']:.4f}")
            print(f"    Recall:    {result['recall']:.4f}")
            print(f"    F1:        {result['f1']:.4f}")
            print(f"    FPR:       {result['fpr']:.4f}")
            print(f"    PR-AUC:    {result['pr_auc']:.4f}")
        
        return results
    
    def tune_contamination(
        self, X_train: pd.DataFrame, X_val: pd.DataFrame, y_val: pd.Series,
        contamination_grid: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """Tune contamination using validation set (Tuesday) for SELECTION only.
        
        Methodology (ISOLATION_FOREST_EXPERIMENT_DESIGN.md section 3.3):
          1. Train Isolation Forest on Monday BENIGN training data with each
             candidate contamination value.
          2. Score Tuesday validation data with each candidate.
          3. Record precision, recall, F1, FPR at each level.
          4. Select by max validation F1 (tie-break: min FPR).
        
        NOTE: Candidate models are NEVER fitted on validation data. The
        validation set is used exclusively for metric-based selection.
        
        Statistical note: for IsolationForest, `contamination` does not change
        tree structure or scores — it only sets offset_ (a quantile of training
        scores). PR-AUC/ROC-AUC are therefore invariant across contamination;
        selection uses threshold-dependent metrics (F1/FPR).
        
        Args:
            X_train: Training feature matrix (Monday BENIGN)
            X_val: Validation feature matrix (Tuesday)
            y_val: Validation labels
            contamination_grid: Values to try
        
        Returns:
            Dictionary with best contamination, threshold and all results
        """
        if contamination_grid is None:
            contamination_grid = CONTAMINATION_GRID
        
        y_binary = (y_val != 'BENIGN').astype(int).values
        
        best_contamination = None
        best_threshold = None
        best_f1 = -1.0
        best_fpr = float('inf')
        all_results = []
        
        for c in contamination_grid:
            # Candidate trained on TRAINING data only; contamination changes
            # only the decision offset, not the trees or scores.
            temp_params = {**self.params, 'contamination': c}
            temp_model = IsolationForest(**temp_params)
            temp_model.fit(X_train.values)
            
            temp_scores = -temp_model.score_samples(X_val.values)
            temp_preds = (temp_model.predict(X_val.values) == -1).astype(int)
            
            precision = precision_score(y_binary, temp_preds, zero_division=0)
            recall = recall_score(y_binary, temp_preds, zero_division=0)
            f1 = f1_score(y_binary, temp_preds, zero_division=0)
            tn, fp, fn, tp = confusion_matrix(y_binary, temp_preds).ravel()
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            
            # Frozen operating point implied by this contamination:
            # anomalies are score >= -offset_ under our negated score convention.
            threshold = float(-temp_model.offset_)
            
            result = {
                'contamination': c,
                'threshold': threshold,
                'precision': float(precision),
                'recall': float(recall),
                'f1': float(f1),
                'fpr': float(fpr),
                'tp': int(tp), 'fp': int(fp), 'fn': int(fn), 'tn': int(tn),
            }
            all_results.append(result)
            
            # Selection: max F1, tie-break lower FPR
            if (f1 > best_f1) or (f1 == best_f1 and fpr < best_fpr):
                best_f1 = f1
                best_fpr = fpr
                best_contamination = c
                best_threshold = threshold
        
        print(f"\n  Contamination tuning results (candidates fitted on TRAIN, selected on VAL):")
        for r in all_results:
            marker = " <-- BEST" if r['contamination'] == best_contamination else ""
            print(f"    c={r['contamination']:.3f}: P={r['precision']:.4f}, R={r['recall']:.4f}, "
                  f"F1={r['f1']:.4f}, FPR={r['fpr']:.6f}{marker}")
        
        return {
            'best_contamination': best_contamination,
            'best_threshold': best_threshold,
            'selection_criterion': 'max validation F1, tie-break min FPR',
            'best_f1': best_f1,
            'all_results': all_results,
        }
    
    def save_model(self, output_path: str = "data/processed/model/isolation_forest.pkl",
                   metadata: Optional[Dict] = None):
        """Save trained model to disk with full provenance metadata."""
        import pickle
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        artifact = {
            'model': self.model,
            'params': self.params,
            'train_samples': self.train_samples,
            'train_time': self.train_time,
            'contamination': self.contamination,
            'metadata': metadata or {},
        }
        with open(output_path, 'wb') as f:
            pickle.dump(artifact, f)
        print(f"Model saved to {output_path}")
    
    def save_results(self, results: Dict, output_path: str = "data/processed/results/experiment_results.json"):
        """Save experiment results to JSON."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {output_path}")
