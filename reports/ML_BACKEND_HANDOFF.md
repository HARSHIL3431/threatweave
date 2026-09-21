# ML → Backend Handoff Contract

**Status**: FROZEN 2026-08-22 — backend development may start against this interface
**Authoritative model artifacts**: see §4
**Companion report**: `reports/FINAL_ML_REPORT.md`

---

## 1. What the ML layer provides

Two frozen Isolation Forest models plus preprocessing configuration:

| | E1 `baseline_no_port` | E2 `with_port` |
|:---|:---|:---|
| Model artifact | `data/processed/experiments/baseline_no_port/model.pkl` | `data/processed/experiments/with_port/model.pkl` |
| Preprocessing config | `.../baseline_no_port/preprocessing_config.json` | `.../with_port/preprocessing_config.json` |
| Feature count | 59 | 60 (includes `Destination Port`) |
| Frozen offset threshold | 0.657668 | 0.521919 |
| Validation-swept threshold (OP-B) | 0.482296 | 0.487850 |
| Contamination | 0.001 | 0.10 |
| Random seed | 42 | 42 |

Each pickle contains: `{model, params, train_samples, train_time, contamination,
metadata}` where `metadata` carries experiment_id, full ordered feature_list,
feature_count, thresholds, seed, training day/dataset, preprocessing summary,
creation_date.

## 2. Input contract (Backend → ML)

- **Schema**: exactly the feature list in the artifact metadata, in that exact
  order, all numeric (float64), one row per network flow.
- Raw CIC-IDS-style flow columns are accepted; the ML layer applies the frozen
  preprocessing chain before scoring:
  1. strip column whitespace; label/metadata columns ignored (never features)
  2. zero-duration handling (`Is_Zero_Duration` flag appended as final column;
     duration floor 1 µs; rate recompute)
  3. drop 8 constant + 10 redundant columns (list in preprocessing config)
  4. log1p on the 24 configured non-negative heavy-tail features;
     signed-log on the 11 configured signed features
     (exact lists in `preprocessing_config.json`)
  5. NO scaling (disabled for both experiments)
- For **E1**, `Destination Port` must be dropped before dedup-equivalent steps;
  for **E2** it is kept. The inference function enforces this from
  `metadata['destination_port_included']`.
- Missing/NaN policy: pipeline verified 0 NaN on full data; a NaN in production
  input is an ERROR CASE (§6), not silently imputed.

## 3. Output contract (ML → Backend)

Per scored flow:

```json
{
    "is_anomaly": true,
    "anomaly_score": 0.612345,
    "threshold": 0.657668,
    "model_version": "isolation_forest_v1",
    "experiment_id": "baseline_no_port",
    "detected_features": [],
    "source_dataset": "CICIDS2017",
    "timestamp": "2026-08-22T12:00:00Z"
}
```

Field definitions:

| Field | Type | Meaning | Status |
|:---|:---|:---|:---|
| `is_anomaly` | bool | score >= threshold at the ACTIVE operating point | AVAILABLE |
| `anomaly_score` | float | negated `score_samples`; higher = more anomalous | AVAILABLE |
| `threshold` | float | the frozen threshold used for `is_anomaly` | AVAILABLE |
| `model_version` | string | semantic version of frozen baseline (`isolation_forest_v1`) | AVAILABLE |
| `experiment_id` | string | `baseline_no_port` or `with_port` | AVAILABLE |
| `detected_features` | list[str] | per-flow feature attribution | **NOT AVAILABLE YET** — no explanation layer exists; do not fabricate |
| `source_dataset` | string | provenance of training corpus | AVAILABLE (static: `"CICIDS2017"`) |
| `timestamp` | ISO-8601 UTC | inference time | AVAILABLE |

Additional recommended fields backend may persist alongside:
`scores_percentile_vs_training` (derivable), `operating_point` (`"OP-A"` /
`"OP-B"` — chosen by backend policy, both are frozen and documented).

## 4. Artifact locations (verified to exist)

```
data/processed/experiments/baseline_no_port/
    model.pkl                     # trained E1 + full metadata
    preprocessing_config.json     # frozen feature lists/order
    results.json                  # tuning grid + val/test metrics
    scores/                       # per-split saved scores + labels (.npy/.csv)
data/processed/experiments/with_port/
    model.pkl
    preprocessing_config.json
    results.json
    scores/
data/processed/analysis/
    analysis_summary.json         # machine-readable pooled/per-day/per-class metrics
    E1_vs_E2_comparison.csv|.md   # headline comparison table
    attack_wise_opA.csv / attack_wise_opB.csv
    fp_profile_E1.csv / fp_profile_E2.csv
    E{1,2}_contamination_grid.csv
    E{1,2}_validation_threshold_sweep.csv
figures/ml/fig1..fig9*.png
```

Inference reference implementation (reload + score, verified by
`scripts/verify_reproducibility.py`, 12/12 PASS):

```python
import pickle, numpy as np, pandas as pd
from preprocess import CICIDS2017Preprocessor

with open("data/processed/experiments/baseline_no_port/model.pkl", "rb") as f:
    art = pickle.load(f)

prep = CICIDS2017Preprocessor(
    apply_scaling=False,
    include_destination_port=art["metadata"]["destination_port_included"],
    verbose=False)
splits = prep.run()                      # or transform a single batch with same stages

scores = -art["model"].score_samples(splits["X_test"]["Friday-DDoS"].values)
preds = scores >= -art["model"].offset_  # frozen OP-A threshold
```

## 5. Expected performance envelope (set expectations in the UI)

At any usable precision the detector catches volumetric DoS/DDoS well
(day PR-AUC 0.51–0.86) and misses Patator/Bot/Web/Infiltration. Benign FPR is
0.09–0.45% at conservative offsets but rises sharply under drift (up to ~42%
on the DDoS day). The dashboard should surface SCORES and drift context, not
binary verdicts alone.

## 6. Error cases

| Case | Behavior |
|:---|:---|
| Column missing vs feature schema | reject batch, error listing missing columns |
| Extra unknown columns | ignore (label/metadata) unless colliding with reserved names → error |
| NaN/Inf in input | error; do not impute (full-data run proved 0 NaN path) |
| Non-numeric value in numeric column | error with row index |
| Model file missing/corrupt | fail fast; never fall back silently to the other experiment |
| Empty batch | return empty result set, not an exception |

## 7. Explicit non-goals (do NOT build into backend)

No retraining endpoints, no threshold mutation API (both operating points are
frozen research decisions D011–D013), no metric recomputation on live traffic,
no use of test-day data for any runtime decision.
