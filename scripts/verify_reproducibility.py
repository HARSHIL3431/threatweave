"""
CICIDS2017 Isolation Forest — Reproducibility Check

Reloads saved model artifacts and preprocessing configuration, re-runs the
deterministic preprocessing pipeline, and verifies that inference on fixed
data slices reproduces the exact scores and predictions recorded during the
experiment run.

Verifies:
  1. Model artifact reloads with complete provenance metadata
  2. Feature order in reproduced splits == saved preprocessing config feature_names
  3. Reloaded model produces identical anomaly scores (float32-exact) on
     held-out slices of validation and test data
  4. Predictions at the frozen threshold are identical

No hidden notebook state is used — only files on disk.

Usage:
    python verify_reproducibility.py
"""

import json
import os
import sys
import pickle
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import CICIDS2017Preprocessor

RESULTS_DIR = '../data/processed/experiments'
SLICE_SIZE = 5000

REQUIRED_METADATA = [
    'experiment_id', 'feature_list', 'feature_count',
    'destination_port_included', 'contamination', 'threshold',
    'random_seed', 'training_dataset', 'training_day',
    'model_params', 'creation_date',
]

EXPERIMENTS = {
    'E1': {'name': 'baseline_no_port', 'include_port': False},
    'E2': {'name': 'with_port', 'include_port': True},
}


def check(exp_key, cfg):
    print(f'\n{"=" * 70}\n{exp_key} ({cfg["name"]})\n{"=" * 70}')
    exp_dir = f'{RESULTS_DIR}/{cfg["name"]}'
    outcomes = []

    def record(name, ok, detail):
        outcomes.append((name, ok, detail))
        print(f'  [{"PASS" if ok else "FAIL"}] {name}: {detail}')

    # --- 1. Load model artifact ---
    with open(f'{exp_dir}/model.pkl', 'rb') as f:
        artifact = pickle.load(f)
    model = artifact['model']
    meta = artifact.get('metadata', {})

    missing_meta = [k for k in REQUIRED_METADATA if k not in meta]
    record('artifact_reload', model is not None,
           f'model.pkl loaded; metadata fields missing: {missing_meta or "none"}')
    record('metadata_complete', not missing_meta,
           f'{len(meta)} metadata fields present')

    with open(f'{exp_dir}/preprocessing_config.json') as f:
        cfg_saved = json.load(f)

    # --- 2. Re-run deterministic preprocessing ---
    print('  Re-running preprocessing (deterministic)...')
    prep = CICIDS2017Preprocessor(
        data_path='../data/combined/CICIDS2017_COMBINED_RAW.csv',
        apply_scaling=False,
        include_destination_port=cfg['include_port'],
        verbose=False,
    )
    splits = prep.run()

    record('feature_order', list(splits['X_val'].columns) == cfg_saved['feature_names'],
           f'reproduced columns match saved config ({len(cfg_saved["feature_names"])} features)')
    record('metadata_feature_list_match', list(splits['X_val'].columns) == meta['feature_list'],
           'model metadata feature list matches reproduced features')

    # --- 3. Score fixed slices with RELOADED model ---
    thr = float(-model.offset_)
    all_ok_scores = True
    all_ok_preds = True
    details = []

    for split_label, X, score_file in [
        ('val_head', splits['X_val'].head(SLICE_SIZE), f'{exp_dir}/scores/val_scores.npy'),
        ('Friday-DDoS_tail', splits['X_test']['Friday-DDoS'].tail(SLICE_SIZE),
         f'{exp_dir}/scores/Friday_DDOS_scores.npy'.replace('DDOS', 'DDoS')),
    ]:
        saved = np.load(score_file.replace('DDos', 'DDoS'))
        # map positional slice to saved array positions
        if split_label == 'val_head':
            saved_slice = saved[:SLICE_SIZE]
        else:
            saved_slice = saved[-SLICE_SIZE:]

        fresh = -model.score_samples(X.values)
        same_scores = np.array_equal(fresh.astype(np.float32), saved_slice)
        max_diff = float(np.max(np.abs(fresh - saved_slice))) if len(saved_slice) else 0.0

        preds_fresh = (fresh >= thr).astype(int)
        preds_saved = (saved_slice >= thr).astype(int)
        same_preds = bool((preds_fresh == preds_saved).all())

        all_ok_scores &= same_scores
        all_ok_preds &= same_preds
        details.append(f'{split_label}: scores_exact={same_scores} '
                       f'(max_diff={max_diff:.2e}), predictions_match={same_preds}')

    record('score_reproduction', all_ok_scores, '; '.join(details))
    record('prediction_reproduction', all_ok_preds,
           'identical anomaly labels at frozen threshold on both slices')

    n_fail = sum(1 for _, ok, _ in outcomes if not ok)
    print(f'  {exp_key} RESULT: {"PASS" if n_fail == 0 else "FAIL"} '
          f'({len(outcomes) - n_fail}/{len(outcomes)} checks passed)')
    return n_fail


total_fail = 0
for exp_key, cfg in EXPERIMENTS.items():
    total_fail += check(exp_key, cfg)

print(f'\n{"=" * 70}')
print(f'REPRODUCIBILITY CHECK: {"PASS" if total_fail == 0 else "FAIL"} '
      f'({total_fail} failed checks total)')
print(f'{"=" * 70}')
sys.exit(1 if total_fail else 0)
