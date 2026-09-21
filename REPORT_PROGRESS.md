# REPORT_PROGRESS.md — Progress Report (Authoritative)

**Last updated**: 2026-08-22
**Phase**: 3 — ML Detection Layer → **COMPLETE**

---

## Executive summary

The CICIDS2017 EDA + baseline ML detection phase is finished. Two leakage-safe
Isolation Forest experiments (E1 without Destination Port, E2 with) were trained
on Monday benign traffic, tuned strictly on Tuesday validation data, and
evaluated once each on six unseen test day sets (≈2.23M / 2.52M post-dedup rows).
Both models, thresholds, grids, per-day metrics, attack-wise breakdowns,
false-positive profiles, and nine figures are frozen artifacts. Reproducibility
was verified by reloading artifacts: **12/12 PASS**.

## What was run

| Step | Result |
|:---|:---|
| Pre-experiment validation gate | 23 PASS / 3 WARN / 0 FAIL |
| Methodology fix pre-run (D011) | tuning candidates fitted on train; selection on val only |
| E1 full run | 300.4 s total; c=0.001; OP-A thr 0.657668; OP-B thr 0.482296 |
| E2 full run | 305.3 s total; c=0.10; OP-A thr 0.521919; OP-B thr 0.487850 |
| Post-analysis | comparison tables, attack-wise CSVs, FP profiles, figures 1–9 |
| Reproducibility | reload + re-inference identical scores (float32-exact), 12/12 |

## Headline results (pooled test, matched operating points)

- OP-A (contamination offsets): E1 F1=0.0005 — Monday-calibrated offsets do not
  transfer across days; E2 F1=0.6264 at FPR=0.132.
- OP-B (validation-swept thresholds): E1 F1=0.6123 (R=0.895, FPR=0.318);
  E2 F1=0.5858 (R=0.716, FPR=0.256).
- Threshold-free separability: Wednesday DoS PR-AUC 0.85–0.86 both;
  Friday DDoS 0.68 (E1) / 0.65 (E2); Friday PortScan 0.03 (E1) vs **0.51 (E2)**.
- Undetectable at usable precision: FTP/SSH-Patator (~0 recall everywhere),
  Bot ≤0.41, Web attacks without port, Infiltration (n=36).
- False positives concentrate in long-idle background service traffic
  (ports 443/80/53/123/88/389/445); FPR doubles-to-quintuples on the drift-heavy
  Friday-DDoS day (up to 42–55%).

## Deliverables

- `reports/FINAL_ML_REPORT.md` — full 17-section report (actual numbers)
- `reports/ML_BACKEND_HANDOFF.md` — frozen ML→backend I/O contract
- `data/processed/experiments/{baseline_no_port,with_port}/` — model.pkl,
  preprocessing_config.json, results.json, scores/
- `data/processed/analysis/` — machine-readable tables/sweeps/profiles
- `figures/ml/fig1..fig9*.png`
- Updated: EXPERIMENTS.md, DECISIONS.md (D011–D013), COMBINED_DATASET_STATUS.md,
  MEMORY.md, TASKS.md, WEEKLY_CHECKPOINT.md

## Status of next phase

READY. Backend + frontend work starts from the frozen contract; no further
dataset/model work is required or permitted without a new experiment ID.
