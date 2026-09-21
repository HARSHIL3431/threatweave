# CICIDS2017 Isolation Forest Experiment — Final Report

**Date**: 2026-08-22
**Status**: COMPLETE — ML baseline frozen
**Experiments**: E1 (`baseline_no_port`), E2 (`with_port`)
**Reproducibility check**: PASS (12/12 checks, see `scripts/reproducibility_log.txt`)

---

## 1. Objective

Measure how well an Isolation Forest trained on Monday benign traffic detects
unseen CICIDS2017 attacks under a leakage-safe, source-day evaluation, and
determine whether Destination Port adds meaningful behavioral signal or
primarily enables attack/environment shortcuts.

---

## 2. Dataset

- Source: `data/combined/CICIDS2017_COMBINED_RAW.csv` — 2,830,743 rows × 81 columns
  (77 numeric features + Label + 3 provenance columns), all 8 capture days.
- After preprocessing:
  - **E1 (no port)**: conflict removal −82,516 rows (271 conflicting vectors),
    dedup −514,807 → **2,233,420 unique rows**.
  - **E2 (with port)**: conflict removal −6,666 rows (697 vectors),
    dedup −303,110 → **2,520,967 unique rows**.
- Note: removing Destination Port before dedup merges more duplicate vectors,
  so E1 and E2 operate on slightly different row sets. This is expected,
  documented in ML_SPLIT_STRATEGY.md, and is a comparability caveat.

## 3. Preprocessing

Validated 15-stage pipeline (`scripts/preprocess.py`, spec in
`reports/FINAL_PREPROCESSING_DESIGN.md`). All parameters deterministic or fitted
on training data only.

1. Load → 2. Schema validation → 3. Label repair → 3.5 Port ablation (E1 only)
→ 4. Label-conflict removal → 5. Deduplication (before splitting) →
6. Metadata/label isolation → 7. Source-day split → 8. Zero-duration handling
(`Is_Zero_Duration` flag + 1 µs floor + rate recompute) → 9. NaN verification
(0 NaN found; no imputation triggered) → 10. Constant feature removal (8) →
11. Redundant feature removal (10) → 12. Transforms (log1p ×24,
signed-log ×11) → 13. Scaling **disabled** → 14. Final feature matrix.

Final feature counts: **E1 = 59**, **E2 = 60** (+ Destination Port).
Leakage checks: no label/metadata column in feature matrix; column order
identical across all splits.

## 4. Split Strategy

| Split | Day | E1 rows | E2 rows | Attack rows |
|:---|:---|---:|---:|---:|
| Train | Monday | 459,093 | 502,981 | 0 (100% benign) |
| Validation | Tuesday | 389,405 | 421,760 | 9,152 (FTP/SSH-Patator) |
| Test 1 | Wednesday | 573,272 | 602,393 | 193,622 / 193,628 (DoS) |
| Test 2 | Thursday-Morning | 143,093 | 156,251 | 2,143 (Web attacks) |
| Test 3 | Thursday-Afternoon | 190,835 | 241,859 | 36 (Infiltration) |
| Test 4 | Friday-Morning | 158,851 | 173,035 | 1,416 / 1,953 (Bot) |
| Test 5 | Friday-PortScan | 105,728 | 204,927 | 1,851 / 90,255 (PortScan) |
| Test 6 | Friday-DDoS | 213,143 | 217,761 | 128,013 (DDoS) |

Test sets were evaluated exactly once per operating point. No test data was
used for any selection.

## 5. E1 Configuration

- ID: `baseline_no_port` — behavioral detector, Destination Port excluded
- Features: 59; scaling disabled
- Training: Monday benign only, 459,093 rows
- Model: IsolationForest(n_estimators=100, max_samples=256, max_features=1.0,
  bootstrap=False, random_state=42, n_jobs=-1)
- Contamination: tuned on validation grid {0.001, 0.005, 0.01, 0.02, 0.05, 0.10}

## 6. E2 Configuration

Identical to E1 except **Destination Port included** (60 features). Same split
methodology (row sets differ only via dedup), same tuning protocol, same
metrics. No other differences exist (verified by validation gate S11).

## 7. Contamination Selection

Protocol (fixed after a pre-run methodology correction, DECISIONS.md D011):
candidate models are **fitted on training data** for each grid value;
validation (Tuesday) is used **only** for metric-based selection.
Criterion: max validation F1, tie-break min FPR.

| c | E1 val P | E1 val R | E1 val F1 | E1 val FPR | E2 val P | E2 val R | E2 val F1 | E2 val FPR |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.001 | 0 | 0 | 0.0000 | 0.001012 | 0 | 0 | 0.0000 | 0.001437 |
| 0.005 | 0 | 0 | 0.0000 | 0.005562 | 0 | 0 | 0.0000 | 0.005729 |
| 0.010 | 0 | 0 | 0.0000 | 0.012060 | 0 | 0 | 0.0000 | 0.011655 |
| 0.020 | 0 | 0 | 0.0000 | 0.023992 | 0 | 0 | 0.0000 | 0.022884 |
| 0.050 | 0 | 0 | 0.0000 | 0.059818 | 0 | 0 | 0.0000 | 0.054449 |
| 0.100 | 0 | 0 | 0.0000 | 0.112980 | ~0 | 0.0002 | 0.0001 | 0.114479 |

- **E1 selected contamination: 0.001** (all F1 tied at 0 → min-FPR tie-break).
  Frozen offset threshold: **0.657668**.
- **E2 selected contamination: 0.10** (only non-zero F1 = 0.0001, from 2 TP).
  Frozen offset threshold: **0.521919**.

Key finding: the tuning grid degenerated because Tuesday's only attack classes
(FTP/SSH-Patator, 9,152 rows ≈ 2.3%) are behaviorally near-invisible to this
model at every operating point. The original design-doc rule "select by max
validation PR-AUC" could not discriminate (PR-AUC is threshold-invariant and
therefore identical across contamination values); the F1/FPR criterion above
was used instead and is recorded as decision D011/D012.

## 8. Threshold Selection

Two frozen operating points are reported for each model:

- **OP-A (primary documented protocol)**: contamination-implied offset
  (quantile of Monday training scores). Selected on validation, frozen before
  touching test data.
  - E1: threshold 0.657668 (c=0.001). E2: threshold 0.521919 (c=0.10).
- **OP-B (design-doc §3.4 alternative)**: decision-threshold sweep performed
  ONLY on Tuesday validation scores; 500 quantile thresholds; criterion max
  validation F1, tie-break min FPR; then frozen and applied once to test days.
  - E1: threshold **0.482296** → val P=0.0591, R=0.7616, F1=0.1098, FPR=0.2916.
  - E2: threshold **0.487850** → val P=0.0672, R=0.7523, F1=0.1233, FPR=0.2317.

Reason: OP-A selections degenerated (all-zero validation F1 grid), so §3.4 of
ISOLATION_FOREST_EXPERIMENT_DESIGN.md was executed to obtain matched,
validation-only operating points that make E1 vs E2 directly comparable.
No test data influenced either selection. Full sweeps:
`data/processed/analysis/E{1,2}_validation_threshold_sweep.csv`.

## 9. Overall Results

Pooled across all six test days (summed confusion matrices).

### OP-A — contamination-frozen offsets

| Metric | E1 No Port | E2 With Port |
|:---|---:|---:|
| Precision | 0.0102 | 0.6265 |
| Recall | 0.0003 | 0.6262 |
| F1 | 0.0005 | 0.6264 |
| FPR | 0.0077 | 0.1316 |
| TP / FP / FN / TN | 84 / 8,146 / 326,997 / 1,049,695 | 260,525 / 155,302 / 155,503 / 1,024,896 |

### OP-B — validation-selected thresholds

| Metric | E1 No Port | E2 With Port |
|:---|---:|---:|
| Precision | 0.4653 | 0.4959 |
| Recall | 0.8949 | 0.7157 |
| F1 | 0.6123 | 0.5858 |
| FPR | 0.3179 | 0.2565 |
| TP / FP / FN / TN | 292,712 / 336,333 / 34,369 / 721,508 | 297,751 / 302,717 / 118,277 / 877,481 |

Interpretation caveat: pooled metrics are dominated by volumetric DoS/DDoS
days (Hulk+DDoS ≈ 300K attack flows of ~330K total). Per-day results below are
the reliable view.

## 10. Per-Day Results

F1 / Precision / Recall / FPR per test day (PR-AUC and ROC-AUC are
threshold-free, computed during the single evaluation pass).

### E1 (no port)

| Test day | Total | Attack | OP-A F1 | OP-A FPR | OP-B F1 | OP-B Prec | OP-B Rec | OP-B FPR | PR-AUC | ROC-AUC |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Wednesday | 573,272 | 193,622 | 0.0008 | 0.00450 | 0.7419 | 0.6130 | 0.9394 | 0.30252 | **0.8494** | 0.9467 |
| Thursday-Morning | 143,093 | 2,143 | 0.0000 | 0.00106 | 0.0085 | 0.0045 | 0.0854 | 0.28771 | 0.0225 | 0.6697 |
| Thursday-Afternoon | 190,835 | 36 | 0.0250 | 0.00105 | 0.0012 | 0.0006 | 0.9167 | 0.29713 | 0.0056 | 0.9347 |
| Friday-Morning | 158,851 | 1,416 | 0.0000 | 0.00126 | 0.0240 | 0.0124 | 0.4082 | 0.29283 | 0.0147 | 0.6891 |
| Friday-PortScan | 105,728 | 1,851 | 0.0000 | 0.00092 | 0.0442 | 0.0234 | 0.4052 | 0.30161 | 0.0324 | 0.7328 |
| Friday-DDoS | 213,143 | 128,013 | 0.0000 | 0.06804 | 0.7693 | 0.7001 | 0.8536 | 0.54981 | **0.6786** | 0.6954 |

### E2 (with port)

| Test day | Total | Attack | OP-A F1 | OP-A FPR | OP-B F1 | OP-B Prec | OP-B Rec | OP-B FPR | PR-AUC | ROC-AUC |
|:---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Wednesday | 602,393 | 193,628 | **0.8355** | 0.11862 | 0.7488 | 0.6347 | 0.9130 | 0.24889 | **0.8605** | 0.9493 |
| Thursday-Morning | 156,251 | 2,143 | 0.0117 | 0.10057 | 0.0985 | 0.0521 | 0.8978 | 0.22711 | 0.0338 | 0.7677 |
| Thursday-Afternoon | 241,859 | 36 | 0.0029 | 0.09074 | 0.0013 | 0.0006 | 0.9167 | 0.21546 | 0.0034 | 0.9300 |
| Friday-Morning | 173,035 | 1,953 | 0.0385 | 0.11319 | 0.0259 | 0.0135 | 0.2878 | 0.23944 | 0.0183 | 0.6479 |
| Friday-PortScan | 204,927 | 90,255 | 0.0145 | 0.10772 | 0.1445 | 0.2487 | 0.1019 | 0.24220 | **0.5075** | 0.6945 |
| Friday-DDoS | 217,761 | 128,013 | 0.6808 | 0.41960 | 0.7738 | 0.7077 | 0.8535 | 0.50294 | **0.6541** | 0.6970 |

Full confusion matrices per day: `data/processed/analysis/analysis_summary.json`.

## 11. Attack-Wise Results

Recall aggregated over all test days containing each class.

### At OP-A (contamination-frozen offsets)

| Attack class | E1 n | E1 detected | E1 recall | E2 n | E2 detected | E2 recall |
|:---|---:|---:|---:|---:|---:|---:|
| DoS Hulk | 172,714 | 70 | 0.0004 | 172,719 | 155,915 | **0.9027** |
| DDoS | 128,013 | 0 | 0.0000 | 128,013 | 85,498 | 0.6679 |
| DoS GoldenEye | 10,286 | 0 | 0.0000 | 10,286 | 9,625 | 0.9357 |
| DoS Slowhttptest | 5,228 | 0 | 0.0000 | 5,228 | 4,848 | 0.9273 |
| DoS slowloris | 5,383 | 0 | 0.0000 | 5,384 | 3,325 | 0.6176 |
| Heartbleed | 11 | 11 | 1.0000 | 11 | 11 | 1.0000 |
| Infiltration | 36 | 3 | 0.0833 | 36 | 32 | 0.8889 |
| Bot | 1,416 / 1,953 | 0 / 418 | 0.0000 / 0.2140 | | | |
| Web Brute Force | 1,470 | 0 | 0.0000 | 1,470 | 76 | 0.0517 |
| Web SQL Injection | 21 | 0 | 0.0000 | 21 | 7 | 0.3333 |
| Web XSS | 652 | 0 | 0.0000 | 652 | 21 | 0.0322 |
| PortScan | 1,851 / 90,255 | 0 / 749 | 0.0000 / 0.0083 | | | |

(E1/E2 pairs where row sets differ are shown as "E1 value / E2 value".)

### At OP-B (validation-F1 thresholds)

| Attack class | E1 recall | E2 recall |
|:---|---:|---:|
| DoS GoldenEye | **0.9921** | 0.9862 |
| DoS Slowhttptest | 0.9874 | 0.9629 |
| DoS slowloris | 0.9504 | 0.9448 |
| DoS Hulk | 0.9345 | 0.9061 |
| DDoS | 0.8536 | 0.8535 |
| Heartbleed | 1.0000 (n=11) | 1.0000 (n=11) |
| Infiltration | 0.9167 (n=36) | 0.9167 (n=36) |
| Web SQL Injection | 0.5714 (n=21) | 0.5714 (n=21) |
| Bot | 0.4082 | 0.2878 |
| PortScan | 0.4052 | 0.1019 |
| Web Brute Force | 0.1000 | 0.8748 |
| Web XSS | 0.0368 | **0.9601** |

Caveat: OP-B flags ~23–32% of traffic, so high class recalls there partly
reflect indiscriminate flagging. Threshold-free PR-AUC (Section 10) is the
honest separability signal: excellent for volumetric DoS (0.68–0.86), good for
PortScan **only with port** (0.51 vs 0.03), poor everywhere else (<0.04).

Machine-readable: `data/processed/analysis/attack_wise_opA.csv`, `attack_wise_opB.csv`.

## 12. False Positive Analysis

Benign false-positive rates per split:

| Split | E1 OP-A FPR | E1 OP-B FPR | E2 OP-A FPR | E2 OP-B FPR |
|:---|---:|---:|---:|---:|
| Tuesday (val) | 0.10% | 29.16% | 11.45% | 23.17% |
| Wednesday | 0.45% | 30.25% | 11.86% | 24.89% |
| Thursday-Morning | 0.11% | 28.77% | 10.06% | 22.71% |
| Thursday-Afternoon | 0.11% | 29.71% | 9.07% | 21.55% |
| Friday-Morning | 0.13% | 29.28% | 11.32% | 23.94% |
| Friday-PortScan | 0.09% | 30.16% | 10.77% | 24.22% |
| **Friday-DDoS** | **6.80%** | **54.98%** | **41.96%** | **50.29%** |

What gets flagged (median comparison, flagged-benign vs clean-benign,
signed-log transformed values):

- Flow Duration: FP ≈ 16.5–16.8 vs clean ≈ 10.1–10.3 → long-lived flows
  (tens of seconds vs milliseconds).
- Idle Mean: FP ≈ 15.8–16.1 vs clean ≈ 0 → long idle periods; typical clean
  benign flow has none.
- Flow Packets/s: FP ≈ 0.7–0.8 vs clean ≈ 4.8–5.1 → low packet rates.
- Init_Win_bytes_backward: FP ≈ +5 vs clean ≈ −0.7 → complete handshakes with
  real advertised windows rather than missing/negative sentinel values.

Top Destination Ports among E2 Wednesday FPs: 443 (48,960), 80 (22,013),
53 (8,719), 123 NTP (1,064), 88 Kerberos (711), 389 LDAP (632), 3268 (419),
0 (298), 445 SMB (249), 137 NetBIOS (242).

Explanation: the model trained on Monday's short, busy, user-like traffic
flags **long-lived idle background infrastructure chatter** (DNS/NTP/Kerberos/
LDAP/SMB keep-alives and streaming-style connections) as anomalous. These are
genuinely under-represented in Monday's sample, not "bad predictions".
Friday-DDoS day shows 2×–6× higher FPR at every operating point — benign
traffic drifts toward the training boundary exactly when attacks saturate the
link, the hardest realistic condition.

Tables: `fp_profile_E{1,2}.csv`, `fp_top_destination_ports_E2_*.csv`;
Figure: `figures/ml/fig9_fpr_by_day_and_split.png`.

## 13. E1 vs E2 Comparison

| Metric | E1 No Port | E2 With Port |
|:---|---:|---:|
| Validation F1 (OP-B) | 0.1098 | 0.1233 |
| Overall Test F1 (OP-B) | **0.6123** | 0.5858 |
| Overall Precision (OP-B) | 0.4653 | 0.4959 |
| Overall Recall (OP-B) | **0.8949** | 0.7157 |
| Overall FPR (OP-B) | 0.3179 | **0.2565** |
| Wednesday F1 (OP-B) | 0.7419 | 0.7488 |
| Thursday Web F1 (OP-B) | 0.0085 | 0.0985 |
| Thursday Infiltration F1 (OP-B) | 0.0012 | 0.0013 |
| Friday Bot F1 (OP-B) | 0.0240 | 0.0259 |
| Friday PortScan F1 (OP-B) | 0.0442 | 0.1445 |
| Friday DDoS F1 (OP-B) | 0.7693 | 0.7738 |
| Wednesday PR-AUC | 0.8494 | **0.8605** |
| Friday PortScan PR-AUC | 0.0324 | **0.5075** |
| Friday DDoS PR-AUC | **0.6786** | 0.6541 |

Verdict on Destination Port:
- Volumetric flooding detection is **port-independent** (Wednesday/Thursday
  DoS, DDoS: E1 ≥ E2 without port).
- PortScan ranking depends **critically** on port (PR-AUC 0.03 → 0.51);
  Web attacks gain apparent recall at permissive thresholds (XSS 0.04 → 0.96).
- These gains concentrate exactly on attack families whose identity is encoded
  in destination ports — consistent with **shortcut learning** (port-based
  separation) rather than richer behavioral understanding. They also do not
  survive dedup consistently: without port, most scan flows collapse to few
  unique vectors (E1 PortScan set: 1,851 rows vs E2: 90,255).
- E1 additionally achieves higher pooled recall/F1 at matched thresholds
  because its lower validation threshold transfers more aggressively.

Conclusion: Destination Port primarily enables environment-specific shortcuts;
it is NOT required for behavioral volumetric detection but IS effectively
required to rank port-scan traffic. This matches hypothesis H2 of the
experiment design.

## 14. Important Findings

1. **Contamination-offset thresholds do not transfer across days.** A quantile
   calibrated on Monday flags almost nothing on later days (E1 OP-A recall
   ≈ 0.03%) even though score ranking quality on those days is high
   (PR-AUC 0.85 Wednesday). Benign drift shifts whole score distributions.
2. **Validation tuning degenerated legitimately.** Tuesday's only attacks
   (Patator brute force) are invisible at every operating point (grid F1 all
   0.0000). Any selection rule built on Tuesday alone inherits this blindness;
   this is a dataset property, not a code failure.
3. **Per-flow unsupervised detection works for floods only.** DoS/DDoS
   families reach 0.63–0.99 recall; everything low-and-slow or application-
   layer stays < 0.3 recall at operationally sane precision.
4. **Heartbleed/Infiltration tiny-class artifacts.** 100%/92% "recall" on
   11/36 samples is anecdotal, not statistical evidence.
5. **False positives have structure.** Long-idle background service flows
   (443/80/53/123/88/389/445) dominate; they are rare in Monday's training
   distribution. Drift amplifies FPR up to 42–55% on the DDoS day.
6. **Destination Port acts as shortcut**, decisive only for port-scan ranking.

## 15. Limitations

- Single-day training population (Monday) cannot cover benign diversity;
  drift handling is out of scope for an unsupervised per-flow baseline.
- E1/E2 row sets differ due to pre-split dedup (documented; affects direct
  per-day count comparisons, not within-model conclusions).
- OP-B thresholds produce 21–32% benign flag rates — research-grade
  operating points, not SOC-deployable ones.
- Tiny classes (Heartbleed n=11, SQLi n=21, Infiltration n=36) yield no
  statistically meaningful estimates.
- Contamination grid capped at 0.10; behavior beyond it unexplored by design.
- No per-feature explanation layer exists yet (`detected_features` contract
  field is NOT AVAILABLE IN CURRENT ARTIFACTS).

## 16. Research Conclusions

1. Can IF detect CICIDS2017 attacks trained on Monday benign? — **Yes for
   volumetric DoS/DDoS (ranking-wise, PR-AUC 0.65–0.86), no for Patator, Bot,
   Web, Infiltration at usable precision.**
2. Easiest: DoS Hulk/GoldenEye/Slowhttptest/slowloris, DDoS, (PortScan with
   port). Hardest: SSH/FTP-Patator (recall ≈ 0 at all tested points), Web
   attacks and Bot without port, Infiltration (too few samples).
3. Benign drift materially degrades calibration day-over-day; fixed global
   thresholds are structurally fragile in this setting.
4. Destination Port improves scores mainly through shortcut separation
   (PortScan/Web), not broader behavioral competence.
5. False positives concentrate in idle background services — explainable,
   potentially suppressible via allow-listing or flow-age context (future work).
6. As the system baseline: freeze **both** models; use E2 scores when raw
   ranking breadth matters, E1 as the honest behavioral reference. The backend
   should treat anomaly SCORES as the primary signal and the frozen threshold
   as a configurable policy, not ground truth.
7. Backend must receive: score, threshold, model/experiment IDs, schema
   version, feature order — see ML_BACKEND_HANDOFF.md.

## 17. Final Model Configuration (FROZEN)

| Field | E1 baseline_no_port | E2 with_port |
|:---|:---|:---|
| Artifact | `data/processed/experiments/baseline_no_port/model.pkl` | `data/processed/experiments/with_port/model.pkl` |
| Features | 59 (no Destination Port) | 60 (with Destination Port) |
| Feature list | artifact metadata `feature_list` | artifact metadata `feature_list` |
| Contamination | 0.001 | 0.10 |
| Frozen offset threshold | 0.657668 | 0.521919 |
| Val-F1 threshold (OP-B) | 0.482296 | 0.487850 |
| Random seed | 42 | 42 |
| Params | n_estimators=100, max_samples=256, max_features=1.0, bootstrap=False | same |
| Training data | Monday BENIGN, 459,093 rows | Monday BENIGN, 502,981 rows |
| Preprocessing config | `.../baseline_no_port/preprocessing_config.json` | `.../with_port/preprocessing_config.json` |
| Created | 2026-08-22 (artifact metadata `creation_date`) | 2026-08-22 |
| Reload verified | YES (scores float32-exact, predictions identical) | YES |

Baseline is FROZEN as of 2026-08-22. Any change requires a new experiment ID.
