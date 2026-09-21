"""
CICIDS2017 End-to-End Pipeline Runner

Runs the complete preprocessing → training → evaluation pipeline.
Supports multiple experiments with different configurations.

Usage:
    python run_pipeline.py                          # Run baseline experiment
    python run_pipeline.py --experiment all         # Run all experiments
    python run_pipeline.py --no-port                # Run without Destination Port
"""

import argparse
import json
import os
import sys
import time
import numpy as np
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import CICIDS2017Preprocessor
from train import IsolationForestTrainer


def run_experiment(
    name: str,
    data_path: str,
    include_port: bool = True,
    apply_scaling: bool = False,
    contamination: float = 0.01,
    tune_on_val: bool = True,
    output_dir: str = "data/processed",
) -> dict:
    """Run a single experiment end-to-end.
    
    Args:
        name: Experiment name (e.g., "baseline", "with_port")
        data_path: Path to combined CSV
        include_port: Whether to include Destination Port
        apply_scaling: Whether to apply RobustScaler
        contamination: Initial contamination value
        tune_on_val: Whether to tune contamination on validation set
        output_dir: Output directory
    
    Returns:
        Experiment results dictionary
    """
    print("=" * 70)
    print(f"EXPERIMENT: {name}")
    print(f"  Destination Port: {'INCLUDED' if include_port else 'EXCLUDED'}")
    print(f"  Scaling: {'ENABLED' if apply_scaling else 'DISABLED'}")
    print(f"  Initial contamination: {contamination}")
    print(f"  Tune on validation: {tune_on_val}")
    print("=" * 70)
    
    start_time = time.time()
    
    # Step 1: Preprocess
    print("\n--- PREPROCESSING ---")
    preprocessor = CICIDS2017Preprocessor(
        data_path=data_path,
        apply_scaling=apply_scaling,
        include_destination_port=include_port,
        verbose=True,
    )
    splits = preprocessor.run()
    
    # Step 2: Train baseline model
    print("\n--- TRAINING ---")
    trainer = IsolationForestTrainer(contamination=contamination)
    trainer.train(splits['X_train'])
    
    # Step 3: Tune contamination on validation (if requested)
    # Candidates are fitted on TRAINING data; validation is used for selection only.
    best_contamination = contamination
    best_threshold = None
    tuning = None
    if tune_on_val:
        print("\n--- CONTAMINATION TUNING (fitted on train, selected on validation) ---")
        tuning = trainer.tune_contamination(splits['X_train'], splits['X_val'], splits['y_val'])
        best_contamination = tuning['best_contamination']
        best_threshold = tuning['best_threshold']
        print(f"\n  Best contamination: {best_contamination}")
    
    # Step 4: Retrain with best contamination and evaluate all test sets
    print("\n--- RETRAINING WITH BEST CONTAMINATION ---")
    trainer = IsolationForestTrainer(contamination=best_contamination)
    trainer.train(splits['X_train'])
    frozen_threshold = float(-trainer.model.offset_)
    
    # Step 5: Evaluate on VALIDATION at the frozen operating point
    print("\n--- VALIDATION EVALUATION (frozen operating point) ---")
    val_results = trainer.evaluate_split(splits['X_val'], splits['y_val'], 'Tuesday-Validation')
    print(f"  Val F1={val_results['f1']:.4f}  Prec={val_results['precision']:.4f}  "
          f"Recall={val_results['recall']:.4f}  FPR={val_results['fpr']:.6f}")
    
    # Step 6: Final evaluation on all test sets (evaluated exactly once)
    print("\n--- EVALUATION (All Test Sets) ---")
    test_results = trainer.evaluate_all(splits)
    
    # Step 7: Persist per-split scores/predictions/labels for offline analysis
    print("\n--- SAVING SCORES FOR ANALYSIS ---")
    scores_dir = f"{output_dir}/experiments/{name}/scores"
    os.makedirs(scores_dir, exist_ok=True)
    np.save(f"{scores_dir}/val_scores.npy", trainer.score(splits['X_val']).astype(np.float32))
    splits['y_val'].to_csv(f"{scores_dir}/val_labels.csv", index=False)
    for day, X_test in splits['X_test'].items():
        safe_day = day.replace('-', '_')
        np.save(f"{scores_dir}/{safe_day}_scores.npy", trainer.score(X_test).astype(np.float32))
        splits['y_test'][day].to_csv(f"{scores_dir}/{safe_day}_labels.csv", index=False)
    print(f"  Scores saved to {scores_dir}")
    
    # Step 8: Save artifacts with full provenance metadata
    exp_dir = f"{output_dir}/experiments/{name}"
    model_metadata = {
        'experiment_id': name,
        'feature_list': list(splits['feature_names']),
        'feature_count': len(splits['feature_names']),
        'destination_port_included': include_port,
        'contamination': best_contamination,
        'threshold': frozen_threshold,
        'random_seed': 42,
        'training_dataset': 'CICIDS2017_COMBINED_RAW.csv',
        'training_day': 'Monday',
        'validation_day': 'Tuesday',
        'test_days': list(splits['X_test'].keys()),
        'preprocessing': {
            'scaling': apply_scaling,
            'zero_duration_flag': True,
            'log1p_transforms': True,
            'signed_log_transforms': True,
            'conflict_removal': True,
            'deduplication': True,
        },
        'model_params': dict(trainer.params),
        'train_samples': int(trainer.train_samples),
        'creation_date': datetime.now().isoformat(),
    }
    trainer.save_model(f"{exp_dir}/model.pkl", metadata=model_metadata)
    
    preprocessor.save_config(f"{exp_dir}/preprocessing_config.json")
    
    # Compile full results
    elapsed = time.time() - start_time
    experiment_results = {
        'experiment_name': name,
        'timestamp': datetime.now().isoformat(),
        'config': {
            'data_path': data_path,
            'include_port': include_port,
            'apply_scaling': apply_scaling,
            'initial_contamination': contamination,
            'tuned_contamination': best_contamination,
            'frozen_threshold': frozen_threshold,
            'threshold_method': 'IsolationForest offset_ (contamination quantile of Monday training scores)',
            'contamination_selection': tuning['selection_criterion'] if tuning else 'fixed',
            'contamination_grid_results': tuning['all_results'] if tuning else None,
            'tune_on_val': tune_on_val,
            'random_seed': 42,
            'train_day': 'Monday',
            'val_day': 'Tuesday',
            'test_days': list(splits['X_test'].keys()),
        },
        'training': {
            'samples': splits['X_train'].shape[0],
            'features': splits['X_train'].shape[1],
            'feature_names': list(splits['feature_names']),
            'train_time_seconds': trainer.train_time,
        },
        'validation_results': val_results,
        'test_results': test_results,
        'elapsed_seconds': elapsed,
    }
    
    trainer.save_results(experiment_results, f"{exp_dir}/results.json")
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"EXPERIMENT '{name}' COMPLETE")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Best contamination: {best_contamination}")
    print(f"\n  Summary across test sets:")
    for day, result in test_results.items():
        print(f"    {day:25s} F1={result['f1']:.4f}  Recall={result['recall']:.4f}  "
              f"Prec={result['precision']:.4f}  FPR={result['fpr']:.4f}  PR-AUC={result['pr_auc']:.4f}")
    print("=" * 70)
    
    return experiment_results


def run_all_experiments(data_path: str, output_dir: str = "data/processed"):
    """Run all planned experiments.
    
    Experiments:
    1. Baseline: Behavioral features WITHOUT Destination Port
    2. With_Port: Same features WITH Destination Port
    3. Scaled: Baseline + RobustScaler (for supervised model consistency)
    """
    results = {}
    
    # Experiment 1: Baseline (no port)
    results['baseline'] = run_experiment(
        name='baseline_no_port',
        data_path=data_path,
        include_port=False,
        apply_scaling=False,
        output_dir=output_dir,
    )
    
    # Experiment 2: With Destination Port
    results['with_port'] = run_experiment(
        name='with_port',
        data_path=data_path,
        include_port=True,
        apply_scaling=False,
        output_dir=output_dir,
    )
    
    # Compare
    print("\n" + "=" * 70)
    print("EXPERIMENT COMPARISON")
    print("=" * 70)
    
    for day in ['Wednesday', 'Friday-DDoS', 'Friday-PortScan']:
        print(f"\n  {day}:")
        for exp_name, exp_results in results.items():
            r = exp_results['test_results'].get(day, {})
            print(f"    {exp_name:20s} F1={r.get('f1', 0):.4f}  "
                  f"Recall={r.get('recall', 0):.4f}  FPR={r.get('fpr', 0):.4f}")
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CICIDS2017 Pipeline Runner")
    parser.add_argument("--data", default="../data/combined/CICIDS2017_COMBINED_RAW.csv")
    parser.add_argument("--experiment", choices=["baseline", "port", "all"], default="baseline")
    parser.add_argument("--no-port", action="store_true", help="Exclude Destination Port")
    parser.add_argument("--scaling", action="store_true", help="Apply RobustScaler")
    parser.add_argument("--contamination", type=float, default=0.01)
    parser.add_argument("--output-dir", default="../data/processed")
    args = parser.parse_args()
    
    if args.experiment == "all":
        run_all_experiments(args.data, args.output_dir)
    elif args.experiment == "baseline":
        run_experiment(
            name='baseline_no_port',
            data_path=args.data,
            include_port=False,
            apply_scaling=args.scaling,
            contamination=args.contamination,
            output_dir=args.output_dir,
        )
    elif args.experiment == "port":
        run_experiment(
            name='with_port',
            data_path=args.data,
            include_port=True,
            apply_scaling=args.scaling,
            contamination=args.contamination,
            output_dir=args.output_dir,
        )
