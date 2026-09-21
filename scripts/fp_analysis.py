"""
CICIDS2017 Isolation Forest — False-Positive Deep-Dive

Re-runs the deterministic preprocessing pipeline for each experiment config,
joins features positionally with the scores saved by run_pipeline.py, and
profiles which benign traffic gets flagged as anomalous.

Answers (research questions):
  - What does flagged benign traffic look like vs clean benign?
  - Which Destination Ports dominate false positives (E2)?
  - Do drift-induced rate/IAT/duration extremes explain the flags?

No model is retrained. No selection happens here (analysis only).

Usage:
    python fp_analysis.py
"""

import json
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from preprocess import CICIDS2017Preprocessor

RESULTS_DIR = '../data/processed/experiments'
ANALYSIS_DIR = '../data/processed/analysis'
FIG_DIR = '../figures/ml'

EXPERIMENTS = {
    'E1': {'name': 'baseline_no_port', 'include_port': False},
    'E2': {'name': 'with_port', 'include_port': True},
}
DAY_ORDER = ['Wednesday', 'Thursday-Morning', 'Thursday-Afternoon',
             'Friday-Morning', 'Friday-PortScan', 'Friday-DDoS']

PROFILE_FEATURES = [
    'Flow Duration', 'Flow Bytes/s', 'Flow Packets/s',
    'Fwd Packets/s', 'Bwd Packets/s',
    'Flow IAT Mean', 'Flow IAT Max', 'Fwd IAT Mean', 'Bwd IAT Max',
    'Active Mean', 'Idle Mean',
    'Total Length of Fwd Packets', 'Total Length of Bwd Packets',
    'Average Packet Size', 'Init_Win_bytes_forward', 'Init_Win_bytes_backward',
    'SYN Flag Count', 'RST Flag Count', 'PSH Flag Count', 'ACK Flag Count',
]

os.makedirs(ANALYSIS_DIR, exist_ok=True)


def load_scores(exp_name):
    base = f'{RESULTS_DIR}/{exp_name}/scores'
    out = {'val_scores': np.load(f'{base}/val_scores.npy')}
    for day in DAY_ORDER:
        safe = day.replace('-', '_')
        out[f'test_{day}'] = np.load(f'{base}/{safe}_scores.npy')
    return out


def summarize_fps(exp_key, cfg):
    print(f'\n=== {exp_key}: preprocessing (deterministic re-run for feature join) ===')
    prep = CICIDS2017Preprocessor(
        data_path='../data/combined/CICIDS2017_COMBINED_RAW.csv',
        apply_scaling=False,
        include_destination_port=cfg['include_port'],
        verbose=False,
    )
    splits = prep.run()
    scores = load_scores(cfg['name'])

    # sanity: positional alignment between saved scores and reproduced splits
    assert len(scores['val_scores']) == len(splits['X_val']), \
        f"val length mismatch {len(scores['val_scores'])} vs {len(splits['X_val'])}"
    for day in DAY_ORDER:
        assert len(scores[f'test_{day}']) == len(splits['X_test'][day]), \
            f"{day} length mismatch"

    with open(f'{RESULTS_DIR}/{cfg["name"]}/results.json') as f:
        res = json.load(f)
    thr_opA = res['config']['frozen_threshold']
    with open(f'{ANALYSIS_DIR}/analysis_summary.json') as f:
        summ = json.load(f)
    thr_opB = summ[exp_key]['opB']['val']['threshold']

    rows = []
    port_tables = {}

    def profile_split(X, y, sc, split_label):
        benign = (y == 'BENIGN').values
        pred_opA = sc >= thr_opA
        pred_opB = sc >= thr_opB
        entry = {'split': split_label,
                 'benign_rows': int(benign.sum()),
                 'fp_opA': int((benign & pred_opA).sum()),
                 'fpr_opA': float((benign & pred_opA).sum() / max(benign.sum(), 1)),
                 'fp_opB': int((benign & pred_opB).sum()),
                 'fpr_opB': float((benign & pred_opB).sum() / max(benign.sum(), 1))}

        fp_mask = benign & pred_opB          # flagged benign at val-selected threshold
        tn_mask = benign & ~pred_opB         # clean benign
        feats = [f for f in PROFILE_FEATURES if f in X.columns]
        for f in feats:
            med_fp = float(X.loc[fp_mask, f].median()) if fp_mask.any() else np.nan
            med_tn = float(X.loc[tn_mask, f].median()) if tn_mask.any() else np.nan
            entry[f'{f}__median_fp'] = med_fp
            entry[f'{f}__median_benign'] = med_tn
        rows.append(entry)

        if 'Destination Port' in X.columns and fp_mask.any():
            ports = X.loc[fp_mask, 'Destination Port'].value_counts().head(15)
            port_tables[split_label] = ports

    print('Profiling validation...')
    profile_split(splits['X_val'], splits['y_val'], scores['val_scores'], 'Tuesday-Validation')
    for day in DAY_ORDER:
        print(f'Profiling test day: {day}')
        profile_split(splits['X_test'][day], splits['y_test'][day], scores[f'test_{day}'], day)

    df = pd.DataFrame(rows)
    df.to_csv(f'{ANALYSIS_DIR}/fp_profile_{exp_key}.csv', index=False)

    for split_label, ports in port_tables.items():
        safe = split_label.replace('-', '_')
        ports.to_csv(f'{ANALYSIS_DIR}/fp_top_destination_ports_{exp_key}_{safe}.csv',
                     header=['flagged_flow_count'])

    # Print compact overview
    show = ['split', 'benign_rows', 'fp_opA', 'fpr_opA', 'fp_opB', 'fpr_opB']
    print(df[show].to_string(index=False))

    key_feats = ['Flow Duration', 'Flow Bytes/s', 'Flow Packets/s',
                 'Flow IAT Mean', 'Idle Mean', 'Init_Win_bytes_backward']
    print('\nMedian comparison (FP benign vs clean benign, OP-B):')
    for split_label in ['Wednesday', 'Friday-DDoS']:
        r = df[df['split'] == split_label].iloc[0]
        parts = [f'--- {split_label} ---']
        for f in key_feats:
            parts.append(f"  {f:28s} FP={r[f + '__median_fp']:>14,.1f}   benign={r[f + '__median_benign']:>14,.1f}")
        if 'Destination Port__top' in df.columns:
            pass
        print('\n'.join(parts))

    if 'Wednesday' in port_tables:
        print('\nTop Destination Ports among Wednesday FPs (E-config):')
        print(port_tables['Wednesday'].head(10).to_string())

    return df, port_tables


all_dfs = {}
for exp_key, cfg in EXPERIMENTS.items():
    df, _ = summarize_fps(exp_key, cfg)
    all_dfs[exp_key] = df

# Figure 9: FP rate per day, both experiments side by side (OP-B)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

plt.rcParams.update({'figure.dpi': 120, 'font.size': 9})
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, (op_col, title) in zip(axes, [('fpr_opA', 'OP-A contamination offset'),
                                      ('fpr_opB', 'OP-B val-F1 threshold')]):
    x = np.arange(len(DAY_ORDER) + 1)
    labels = ['Val\n(Tuesday)'] + [d.replace('-', '\n') for d in DAY_ORDER]
    v1 = all_dfs['E1'][op_col].values
    v2 = all_dfs['E2'][op_col].values
    ax.bar(x - 0.2, v1, width=0.4, label='E1 no port', color='#4878CF')
    ax.bar(x + 0.2, v2, width=0.4, label='E2 with port', color='#D65F5F')
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel('Benign false-positive rate')
    ax.set_title(title)
    ax.legend(fontsize=8)
fig.suptitle('Fig 9. Benign traffic flagged as anomalous — split by split')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig9_fpr_by_day_and_split.png')
plt.close(fig)

print(f'\nFP analysis complete -> {ANALYSIS_DIR}, figure -> {FIG_DIR}')
