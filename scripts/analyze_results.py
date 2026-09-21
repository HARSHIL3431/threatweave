"""
CICIDS2017 Isolation Forest — Post-Experiment Analysis

Consumes artifacts produced by run_pipeline.py (results.json + saved scores/labels)
and produces:
  1. E1 vs E2 comparison tables (overall, per-day)
  2. Validation-only threshold sweep (design doc section 3.4) with frozen
     val-selected thresholds applied to test sets (evaluation only)
  3. Attack-wise aggregated detection tables
  4. All required figures (validation/test score distributions, confusion
     matrices, metric comparisons, attack-wise recall, FPR by day)

No model is retrained. Test data is never used for selection.

Usage:
    python analyze_results.py
"""

import json
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RESULTS_DIR = '../data/processed/experiments'
ANALYSIS_DIR = '../data/processed/analysis'
FIG_DIR = '../figures/ml'

EXPERIMENTS = {
    'E1': 'baseline_no_port',
    'E2': 'with_port',
}
DAY_ORDER = ['Wednesday', 'Thursday-Morning', 'Thursday-Afternoon',
             'Friday-Morning', 'Friday-PortScan', 'Friday-DDoS']

os.makedirs(ANALYSIS_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def load_experiment(exp_key):
    """Load results.json and all saved scores/labels for one experiment."""
    name = EXPERIMENTS[exp_key]
    base = f'{RESULTS_DIR}/{name}'
    with open(f'{base}/results.json') as f:
        results = json.load(f)

    data = {'results': results, 'name': name, 'scores': {}, 'labels': {}}

    val_scores = np.load(f'{base}/scores/val_scores.npy')
    val_labels = pd.read_csv(f'{base}/scores/val_labels.csv')['Label']
    data['val_scores'] = val_scores
    data['val_labels'] = val_labels

    for day in DAY_ORDER:
        safe = day.replace('-', '_')
        data['scores'][day] = np.load(f'{base}/scores/{safe}_scores.npy')
        data['labels'][day] = pd.read_csv(f'{base}/scores/{safe}_labels.csv')['Label']

    return data


def binary_labels(y):
    return (y != 'BENIGN').astype(int).values


def metrics_at_threshold(y_bin, scores, thr):
    preds = (scores >= thr).astype(int)
    tp = int(((preds == 1) & (y_bin == 1)).sum())
    fp = int(((preds == 1) & (y_bin == 0)).sum())
    fn = int(((preds == 0) & (y_bin == 1)).sum())
    tn = int(((preds == 0) & (y_bin == 0)).sum())
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {'threshold': float(thr), 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': precision, 'recall': recall, 'f1': f1, 'fpr': fpr}


def sweep_validation_f1(scores, y_bin, n_points=500):
    """Sweep thresholds on validation scores; return full sweep + F1-optimal point.

    Thresholds are taken as score quantiles of the validation distribution.
    Selection: max F1, tie-break min FPR.
    """
    qs = np.linspace(0.00001, 0.99999, n_points)
    thresholds = np.quantile(scores, qs)
    best = None
    rows = []
    for thr in thresholds:
        m = metrics_at_threshold(y_bin, scores, thr)
        rows.append({'quantile': None, **m})
        key = (m['f1'], -m['fpr'])
        if best is None or key > best[0]:
            best = (key, m)
    sweep = pd.DataFrame(rows)
    # annotate quantile of each threshold
    sweep['quantile'] = [float((scores <= t).mean()) for t in sweep['threshold']]
    return sweep, best[1]


def pooled_overall(per_day):
    """Pool confusion matrices across test days."""
    tp = sum(m['tp'] for m in per_day.values())
    fp = sum(m['fp'] for m in per_day.values())
    fn = sum(m['fn'] for m in per_day.values())
    tn = sum(m['tn'] for m in per_day.values())
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
            'precision': precision, 'recall': recall, 'f1': f1, 'fpr': fpr}


# ============================================================
# MAIN ANALYSIS
# ============================================================

print('=' * 70)
print('CICIDS2017 ISOLATION FOREST — POST-EXPERIMENT ANALYSIS')
print('=' * 70)

exps = {k: load_experiment(k) for k in EXPERIMENTS}
summary = {}

for exp_key, d in exps.items():
    res = d['results']
    print(f'\n--- {exp_key} ({d["name"]}) ---')
    print(f"  Contamination: {res['config']['tuned_contamination']}  "
          f"Frozen offset threshold: {res['config']['frozen_threshold']:.6f}")

    # --- Contamination grid table ---
    grid = pd.DataFrame(res['config']['contamination_grid_results'])
    grid.to_csv(f'{ANALYSIS_DIR}/{exp_key}_contamination_grid.csv', index=False)

    y_val_bin = binary_labels(d['val_labels'])

    # Operating point A: contamination-frozen offset (as run by pipeline)
    thr_contam = res['config']['frozen_threshold']
    opA_val = metrics_at_threshold(y_val_bin, d['val_scores'], thr_contam)

    # Per-day test at operating point A
    opA_test_days = {}
    for day in DAY_ORDER:
        yb = binary_labels(d['labels'][day])
        opA_test_days[day] = metrics_at_threshold(yb, d['scores'][day], thr_contam)
    opA_test = pooled_overall(opA_test_days)

    # Operating point B: validation-selected F1-optimal threshold (design doc 3.4)
    sweep, best_thr = sweep_validation_f1(d['val_scores'], y_val_bin)
    sweep.to_csv(f'{ANALYSIS_DIR}/{exp_key}_validation_threshold_sweep.csv', index=False)
    opB_val = dict(best_thr)
    opB_test_days = {}
    for day in DAY_ORDER:
        yb = binary_labels(d['labels'][day])
        opB_test_days[day] = metrics_at_threshold(yb, d['scores'][day], best_thr['threshold'])
    opB_test = pooled_overall(opB_test_days)

    print(f'  OP-A (contamination offset): val F1={opA_val["f1"]:.4f} '
          f'(P={opA_val["precision"]:.4f} R={opA_val["recall"]:.4f} FPR={opA_val["fpr"]:.4f})')
    print(f'  OP-B (val F1-optimal thr={best_thr["threshold"]:.6f}): '
          f'val F1={best_thr["f1"]:.4f} (P={best_thr["precision"]:.4f} '
          f'R={best_thr["recall"]:.4f} FPR={best_thr["fpr"]:.4f})')

    # PR-AUC / ROC-AUC per day come straight from pipeline results.json
    prauc_days = {day: res['test_results'][day]['pr_auc'] for day in DAY_ORDER}
    rocauc_days = {day: res['test_results'][day]['roc_auc'] for day in DAY_ORDER}

    summary[exp_key] = {
        'contamination': res['config']['tuned_contamination'],
        'threshold_offset': thr_contam,
        'grid': grid.to_dict('records'),
        'opA': {'val': opA_val, 'test_pooled': opA_test, 'test_by_day': opA_test_days},
        'opB': {'val': opB_val, 'test_pooled': opB_test, 'test_by_day': opB_test_days,
                'selection': 'max validation F1, tie-break min FPR'},
        'pr_auc_days': prauc_days,
        'roc_auc_days': rocauc_days,
        'attack_counts': {day: res['test_results'][day].get('attack_counts', {})
                          for day in DAY_ORDER},
    }

    d['sweep'] = sweep
    d['best_thr'] = best_thr
    d['opA_test_days'] = opA_test_days
    d['opB_test_days'] = opB_test_days

# ============================================================
# COMPARISON TABLES
# ============================================================

print('\n' + '=' * 70)
print('E1 vs E2 COMPARISON')
print('=' * 70)

rows = []
for metric_label, getter in [
    ('Validation F1 (OP-B)', lambda s: s['opB']['val']['f1']),
    ('Overall Test F1 (OP-B)', lambda s: s['opB']['test_pooled']['f1']),
    ('Overall Precision (OP-B)', lambda s: s['opB']['test_pooled']['precision']),
    ('Overall Recall (OP-B)', lambda s: s['opB']['test_pooled']['recall']),
    ('Overall FPR (OP-B)', lambda s: s['opB']['test_pooled']['fpr']),
    ('Validation F1 (OP-A)', lambda s: s['opA']['val']['f1']),
    ('Overall Test F1 (OP-A)', lambda s: s['opA']['test_pooled']['f1']),
    ('Overall Precision (OP-A)', lambda s: s['opA']['test_pooled']['precision']),
    ('Overall Recall (OP-A)', lambda s: s['opA']['test_pooled']['recall']),
    ('Overall FPR (OP-A)', lambda s: s['opA']['test_pooled']['fpr']),
]:
    rows.append({'Metric': metric_label,
                 'E1 No Port': getter(summary['E1']),
                 'E2 With Port': getter(summary['E2'])})

for day in DAY_ORDER:
    rows.append({'Metric': f'{day} F1 (OP-B)',
                 'E1 No Port': summary['E1']['opB']['test_by_day'][day]['f1'],
                 'E2 With Port': summary['E2']['opB']['test_by_day'][day]['f1']})
for day in DAY_ORDER:
    rows.append({'Metric': f'{day} PR-AUC',
                 'E1 No Port': summary['E1']['pr_auc_days'][day],
                 'E2 With Port': summary['E2']['pr_auc_days'][day]})

cmp_df = pd.DataFrame(rows)
cmp_df.to_csv(f'{ANALYSIS_DIR}/E1_vs_E2_comparison.csv', index=False)
with open(f'{ANALYSIS_DIR}/E1_vs_E2_comparison.md', 'w') as f:
    f.write('| Metric | E1 No Port | E2 With Port |\n|---|---:|---:|\n')
    for _, r in cmp_df.iterrows():
        f.write(f"| {r['Metric']} | {r['E1 No Port']:.4f} | {r['E2 With Port']:.4f} |\n")
print(cmp_df.to_string(index=False))

# ============================================================
# ATTACK-WISE AGGREGATION
# ============================================================

print('\n' + '=' * 70)
print('ATTACK-WISE DETECTION (aggregated across test days)')
print('=' * 70)

for op_key, label in [('opA', 'Contamination offset'), ('opB', 'Val-F1 threshold')]:
    agg_rows = []
    classes = sorted({c for s in summary.values()
                      for day_counts in s['attack_counts'].values()
                      for c in day_counts})
    for cls in classes:
        row = {'Attack Class': cls}
        for exp_key in ['E1', 'E2']:
            samples = sum(summary[exp_key]['attack_counts'][day].get(cls, {}).get('samples', 0)
                          for day in DAY_ORDER)
            tp = sum(summary[exp_key]['attack_counts'][day].get(cls, {}).get('tp', 0)
                     for day in DAY_ORDER)
            # recall at this operating point recomputed from saved scores
            detected = 0
            total = 0
            for day in DAY_ORDER:
                y = exps[exp_key]['labels'][day]
                mask = (y == cls).values
                if mask.sum() == 0:
                    continue
                thr = summary[exp_key][op_key]['val']['threshold']
                preds = (exps[exp_key]['scores'][day] >= thr).astype(int)
                detected += int(preds[mask].sum())
                total += int(mask.sum())
            rec = detected / total if total else 0.0
            row[f'{exp_key} samples'] = total
            row[f'{exp_key} detected'] = detected
            row[f'{exp_key} recall'] = rec
        agg_rows.append(row)
    agg_df = pd.DataFrame(agg_rows)
    agg_df.to_csv(f'{ANALYSIS_DIR}/attack_wise_{op_key}.csv', index=False)
    print(f'\n[{label}]')
    print(agg_df.to_string(index=False))

# ============================================================
# FIGURES
# ============================================================

plt.rcParams.update({'figure.dpi': 120, 'font.size': 9})

COLOR_BENIGN = '#4878CF'
COLOR_ATTACK = '#D65F5F'
COLORS12 = ['#4878CF', '#D65F5F']


def score_hist(ax, scores_benign, scores_attack, thr, title):
    bins = np.linspace(0, max(1e-6, np.quantile(np.concatenate([scores_benign, scores_attack]), 0.999)), 80)
    ax.hist(scores_benign, bins=bins, alpha=0.55, density=True, color=COLOR_BENIGN, label='Benign')
    ax.hist(scores_attack, bins=bins, alpha=0.55, density=True, color=COLOR_ATTACK, label='Attack')
    ax.axvline(thr, color='black', ls='--', lw=1.2, label=f'Threshold={thr:.4f}')
    ax.set_title(title)
    ax.set_xlabel('Anomaly score (higher = more anomalous)')
    ax.set_ylabel('Density')
    ax.legend(fontsize=7)


# FIG 1: validation score distributions
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, exp_key in zip(axes, ['E1', 'E2']):
    y_bin = binary_labels(exps[exp_key]['val_labels'])
    sc = exps[exp_key]['val_scores']
    thr = summary[exp_key]['threshold_offset']
    score_hist(ax, sc[y_bin == 0], sc[y_bin == 1], thr,
               f'{exp_key} Validation (Tuesday) scores\n'
               f'{"no" if exp_key == "E1" else "with"} Destination Port')
fig.suptitle('Fig 1. Validation anomaly-score distributions vs frozen Monday-offset thresholds')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig1_validation_score_distributions.png')
plt.close(fig)

# FIG 2: test score distributions per day (both experiments)
fig, axes = plt.subplots(len(DAY_ORDER), 2, figsize=(11, 3 * len(DAY_ORDER)))
for i, day in enumerate(DAY_ORDER):
    for j, exp_key in enumerate(['E1', 'E2']):
        ax = axes[i, j]
        y_bin = binary_labels(exps[exp_key]['labels'][day])
        sc = exps[exp_key]['scores'][day]
        thr = summary[exp_key]['threshold_offset']
        score_hist(ax, sc[y_bin == 0], sc[y_bin == 1], thr,
                   f'{exp_key} — {day}')
fig.suptitle('Fig 2. Test anomaly-score distributions by day (benign vs attack)')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig2_test_score_distributions.png')
plt.close(fig)


def confusion_matrix_fig(ax, tp, fp, fn, tn, title):
    mat = np.array([[tn, fp], [fn, tp]])
    im = ax.imshow(mat, cmap='Blues')
    for (i, j), v in np.ndenumerate(mat):
        ax.text(j, i, f'{v:,}', ha='center', va='center',
                color='white' if v > mat.max() / 2 else 'black', fontsize=9)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['Pred benign', 'Pred anomaly'])
    ax.set_yticks([0, 1]); ax.set_yticklabels(['True benign', 'True attack'])
    ax.set_title(title)


# FIG 3: confusion matrices (pooled test) both operating points
fig, axes = plt.subplots(2, 2, figsize=(10, 8))
for j, exp_key in enumerate(['E1', 'E2']):
    oA = summary[exp_key]['opA']['test_pooled']
    oB = summary[exp_key]['opB']['test_pooled']
    confusion_matrix_fig(axes[0, j], oA['tp'], oA['fp'], oA['fn'], oA['tn'],
                         f'{exp_key} pooled test — OP-A contamination offset')
    confusion_matrix_fig(axes[1, j], oB['tp'], oB['fp'], oB['fn'], oB['tn'],
                         f'{exp_key} pooled test — OP-B val-F1 threshold')
fig.suptitle('Fig 3. Pooled test confusion matrices')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig3_confusion_matrices.png')
plt.close(fig)

# FIG 4: E1 vs E2 metric comparison (per-day F1 at OP-B + PR-AUC)
x = np.arange(len(DAY_ORDER))
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, key, title in [(axes[0], 'f1', 'Per-day F1 (val-F1 threshold)'),
                       (axes[1], 'pr_auc', 'Per-day PR-AUC (threshold-free)')]:
    src = summary['E1']['opB']['test_by_day'] if key == 'f1' else summary['E1']['pr_auc_days']
    src2 = summary['E2']['opB']['test_by_day'] if key == 'f1' else summary['E2']['pr_auc_days']
    v1 = [src[d][key] if isinstance(src[d], dict) else src[d] for d in DAY_ORDER]
    v2 = [src2[d][key] if isinstance(src2[d], dict) else src2[d] for d in DAY_ORDER]
    ax.bar(x - 0.2, v1, width=0.4, label='E1 no port', color=COLORS12[0])
    ax.bar(x + 0.2, v2, width=0.4, label='E2 with port', color=COLORS12[1])
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace('-', '\n') for d in DAY_ORDER], fontsize=7)
    ax.set_ylim(0, 1)
    ax.set_title(title)
    ax.legend(fontsize=8)
fig.suptitle('Fig 4. E1 vs E2 detection performance by test day')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig4_E1_vs_E2_comparison.png')
plt.close(fig)

# FIG 5: attack-wise recall (OP-B), aggregated across days
agg = pd.read_csv(f'{ANALYSIS_DIR}/attack_wise_opB.csv')
classes = agg['Attack Class'].tolist()
xx = np.arange(len(classes))
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.bar(xx - 0.2, agg['E1 recall'], width=0.4, label='E1 no port', color=COLORS12[0])
ax.bar(xx + 0.2, agg['E2 recall'], width=0.4, label='E2 with port', color=COLORS12[1])
ax.set_xticks(xx)
ax.set_xticklabels([c.replace(' ', '\n').replace('-', ' ') for c in classes], fontsize=7)
ax.set_ylabel('Recall (aggregated across test days)')
ax.set_ylim(0, 1)
ax.axhline(0.9, color='gray', ls=':', lw=0.8)
ax.set_title('Fig 5. Attack-wise recall at validation-selected threshold')
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig5_attack_wise_recall.png')
plt.close(fig)

# FIG 6: FPR by test day (both operating points)
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, op_key, title in [(axes[0], 'opA', 'OP-A contamination offset'),
                          (axes[1], 'opB', 'OP-B val-F1 threshold')]:
    v1 = [summary['E1'][op_key]['test_by_day'][d]['fpr'] for d in DAY_ORDER]
    v2 = [summary['E2'][op_key]['test_by_day'][d]['fpr'] for d in DAY_ORDER]
    ax.bar(x - 0.2, v1, width=0.4, label='E1 no port', color=COLORS12[0])
    ax.bar(x + 0.2, v2, width=0.4, label='E2 with port', color=COLORS12[1])
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace('-', '\n') for d in DAY_ORDER], fontsize=7)
    ax.set_ylabel('False positive rate (benign flagged)')
    ax.set_title(title)
    ax.legend(fontsize=8)
fig.suptitle('Fig 6. False-positive rate by test day')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig6_fpr_by_day.png')
plt.close(fig)

# FIG 7: detection performance per attack class with sample counts annotated
fig, ax = plt.subplots(figsize=(11, 4.5))
det = agg['E2 detected'] / agg['E2 samples'].clip(lower=1)
sc_sizes = agg['E1 samples'] + agg['E2 samples']
bars = ax.bar(xx, agg['E2 recall'], width=0.6, color=COLORS12[1], alpha=0.85)
for i, c in enumerate(classes):
    n = int(sc_sizes[i])
    ax.text(i, min(1.02, agg['E2 recall'][i] + 0.02), f'n={n:,}',
            ha='center', fontsize=6, rotation=90)
ax.set_xticks(xx)
ax.set_xticklabels([c.replace(' ', '\n') for c in classes], fontsize=7)
ax.set_ylabel('Recall (E2, val-F1 threshold)')
ax.set_ylim(0, 1.15)
ax.set_title('Fig 7. Attack-class detection performance with sample counts (E1+E2 pooled rows)')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig7_attack_class_detection.png')
plt.close(fig)

# FIG 8: validation F1-vs-threshold sweep curves (documents threshold selection)
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, exp_key in zip(axes, ['E1', 'E2']):
    sw = exps[exp_key]['sweep']
    ax.plot(sw['threshold'], sw['f1'], lw=1.5, label='F1', color='#333333')
    ax.plot(sw['threshold'], sw['recall'], lw=1, ls='--', label='Recall', color=COLOR_ATTACK)
    ax.plot(sw['threshold'], sw['precision'], lw=1, ls='--', label='Precision', color=COLOR_BENIGN)
    bt = exps[exp_key]['best_thr']['threshold']
    ax.axvline(bt, color='green', lw=1.2, label=f'Selected={bt:.4f}')
    ax.set_xscale('log')
    ax.set_xlabel('Threshold (log scale)')
    ax.set_title(f'{exp_key} validation sweep (Tuesday only)')
    ax.legend(fontsize=7)
fig.suptitle('Fig 8. Threshold selection on validation data only (design doc §3.4)')
fig.tight_layout()
fig.savefig(f'{FIG_DIR}/fig8_validation_threshold_sweep.png')
plt.close(fig)

# Save machine-readable summary
with open(f'{ANALYSIS_DIR}/analysis_summary.json', 'w') as f:
    json.dump(summary, f, indent=2, default=float)

print(f'\nAnalysis complete.')
print(f'  Tables:   {ANALYSIS_DIR}')
print(f'  Figures:  {FIG_DIR}')
