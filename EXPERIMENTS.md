# EXPERIMENTS.md

Tracks all ML experiments. Each experiment has a hypothesis, configuration, results, and conclusion.

---

## Experiment Matrix

| ID | Name | Port | Scaling | Contamination | Features | Status |
|:---|:---|:---|:---|:---|:---|:---|
| E1 | baseline_no_port | NO | NO | 0.001 (tuned on val) | 59 | COMPLETE |
| E2 | with_port | YES | NO | 0.10 (tuned on val) | 60 | COMPLETE |

Run date: 2026-08-22. Full results: `reports/FINAL_ML_REPORT.md`,
`data/processed/analysis/`. Reproducibility: PASS (12/12).

---

## E1: Baseline Behavioral Detection (No Port)

**Hypothesis**: Isolation Forest can detect attacks using only behavioral flow features, without relying on Destination Port memorization.

**Configuration**:
- Features: 59 (77 numeric − port − 8 constant − 10 redundant + Is_Zero_Duration)
- Preprocessing: Full validated pipeline; scaling disabled
- Training: Monday BENIGN (459,093 rows)
- Validation: Tuesday (389,405 rows; 9,152 attacks = FTP/SSH-Patator)
- Test: Wednesday / Thursday-Morning / Thursday-Afternoon / Friday-Morning / Friday-PortScan / Friday-DDoS
- Contamination grid {0.001–0.10} fitted on TRAIN, selected on VAL
  (max F1, tie-break min FPR). ALL grid F1 = 0.0000 → c=0.001 via tie-break.
- Operating points frozen before test evaluation:
  OP-A offset threshold 0.657668; OP-B validation-swept threshold 0.482296
  (val P=0.0591 R=0.7616 F1=0.1098 FPR=0.2916)

**Results**:
- OP-A pooled test: P=0.0102, R=0.0003, F1=0.0005, FPR=0.0077 → offset thresholds do not transfer across days.
- OP-B pooled test: P=0.4653, R=0.8949, F1=0.6123, FPR=0.3179.
- Threshold-free day PR-AUC: Wed **0.849**, Thu-Web 0.022, Thu-Infil 0.006,
  Fri-Bot 0.015, Fri-PortScan 0.032, Fri-DDoS **0.679**.
- Best classes (OP-B recall): DoS GoldenEye 0.992, Slowhttptest 0.987,
  slowloris 0.950, Hulk 0.934, DDoS 0.854, Heartbleed 11/11.
- Missed: Patators ≈ 0 at all points; Bot 0.41; Web ≤ 0.10.

**Conclusion**: Behavioral-only scores rank volumetric floods well but Monday-calibrated offsets are unusable on later days (benign drift). At matched validation-selected thresholds detection is broad but indiscriminate (FPR ~30%). Port-scan traffic is essentially invisible without port features.

---

## E2: Port-Included Detection

**Hypothesis**: Including Destination Port inflates detection metrics due to memorization rather than behavioral detection.

**Configuration**: Same as E1 with Destination Port included (60 features).
Training 502,981 rows; validation 421,760 (same 9,152 Patator attacks).
Contamination c=0.10 selected (only non-zero grid F1=0.0001 from 2 TP).
OP-A offset threshold 0.521919; OP-B threshold 0.487850
(val P=0.0672 R=0.7523 F1=0.1233 FPR=0.2317).

**Results**:
- OP-A pooled test: P=0.6265, R=0.6262, F1=0.6264, FPR=0.1316.
- Per-day OP-A F1: Wed **0.836** (P=0.78, R=0.90), Fri-DDoS 0.681;
  other days < 0.04 at FPR ≈ 10%.
- Threshold-free day PR-AUC: Wed **0.861**, Thu-Web 0.034, Fri-PortScan **0.507**,
  Fri-DDoS 0.654.
- Attack-wise (OP-B): XSS 0.960, Web-BruteForce 0.875, Infiltration 32/36,
  Hulk 0.906, DDoS 0.854; PortScan only 0.102 despite PR-AUC 0.507.

**Conclusion**: The port feature mainly enables shortcut separation of port-correlated families (PortScan ranking jumps 0.03→0.51; Web recall rises at permissive thresholds) while adding nothing to volumetric behavioral detection (Wed/DDoS PR-AUC unchanged or lower). Supports H2: gains are environment-specific, not richer behavior.

---

## Head-to-Head (matched operating points)

| Metric | E1 No Port | E2 With Port |
|:---|---:|---:|
| Overall Test F1 (OP-B) | **0.6123** | 0.5858 |
| Overall Recall (OP-B) | **0.8949** | 0.7157 |
| Overall FPR (OP-B) | 0.3179 | **0.2565** |
| Friday PortScan PR-AUC | 0.0324 | **0.5075** |

Both models FROZEN as of 2026-08-22 (DECISIONS.md D013). No further tuning permitted without a new experiment ID.

## Experiment Execution

```bash
cd demo/scripts
python run_pipeline.py --experiment all      # E1 then E2 (~10 min)
python analyze_results.py                    # tables + figures 1-8
python fp_analysis.py                        # FP deep-dive + figure 9
python verify_reproducibility.py             # artifact reload check (12/12)
```
