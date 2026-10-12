# Frozen E2 Detector Evaluation (P1-8) — Descriptive Evidence, Not a New Model

Evaluation-only phase under DI-005. Nothing was trained, tuned, or modified:
thresholds, preprocessing, feature order, artifacts, and response contracts
are exactly as validated. Results below characterize the frozen detector;
they do not certify live-traffic performance.

## 1. Protocol and lineage

- **Model:** E2 `with_port`, 60 features, IsolationForest(contamination=0.10,
  seed 42), trained on Monday BENIGN only (502,981 rows per experiment record).
- **Score:** `-score_samples()`; higher means more anomalous.
- **Thresholds:** OP-A `0.5219193851693676` (contamination quantile of Monday
  training scores, frozen before test evaluation); OP-B `0.4878500998020172`
  (max-validation-F1 sweep on Tuesday, tie-break min FPR). Both semantics are
  documented in `results.json` (`threshold_method`, `contamination_selection`)
  — no interpretation gap to flag.
- **Decision:** `score >= threshold`, verified in serving code and tests.
- **Inputs:** saved pipeline scores/labels in
  `data/processed/experiments/with_port/scores/` (val + 6 test days), read
  with chunked accumulation and a two-chunk-size self-check (identical).
  Positive class: `Label != "BENIGN"` after whitespace strip. Empty/missing
  labels would be excluded and counted — **0 such rows occurred**.
- **Production-path fidelity:** saved scores were proven identical to live
  inference by `verify_reproducibility.py` (12/12 float32-exact, P1-1) and
  `test_ml_consistency` (API == pipeline). This phase recomputes aggregates
  from those scores; it does not re-derive them through a parallel pipeline.
- **Lineage classification:** Monday=train (in-sample, not scored here);
  Tuesday=validation touched by contamination tuning AND OP-B sweep
  (**descriptive for both OPs**); the 6 test days were never used in
  selection (**honest holdout for both OPs**, same-lab caveats below).
- **Manifest:** `data/processed/analysis/detector_eval_p18/manifest.json`
  pins script version, thresholds, feature count, label rule, all 8 raw-CSV
  SHA-256 hashes, and both frozen-artifact hashes.

## 2. Coverage

7 of 8 partitions scored (all saved-score splits). Monday (train) has no
saved scores and is in-sample regardless — explicitly out of scope, not a
gap in holdout coverage. Total evaluated: 2,017,986 records (421,760 val +
1,596,226 test).

## 3. Aggregate metrics (positive class: non-BENIGN)

Test-days-only pooled (6 files, honest holdout):

| OP | TP | FP | TN | FN | Precision | Recall | F1 | FPR | Spec. | Bal. acc. |
|---|---|---|---|---|---|---|---|---|---|---|
| OP-A | 260,525 | 155,302 | 1,024,896 | 155,503 | 0.6265 | 0.6262 | 0.6264 | 0.1316 | 0.8684 | 0.7473 |
| OP-B | 297,751 | 302,717 | 877,481 | 118,277 | 0.4959 | 0.7157 | 0.5858 | 0.2565 | 0.7435 | 0.7296 |

These reproduce the documented experiment record exactly (OP-A F1 0.6264,
OP-B F1 0.5858). Accuracy is not reported as a quality measure under this
class imbalance; balanced accuracy is given instead. No zero denominators
occurred in pooled aggregates.

## 4. Per-file findings (OP-A / OP-B F1; PR-AUC threshold-free)

| Split | n attack | OP-A (P/R/F1/FPR) | OP-B (P/R/F1/FPR) | PR-AUC | ROC-AUC |
|---|---|---|---|---|---|
| Wednesday | 193,628 | 0.78/0.90/**0.836**/0.12 | 0.63/0.91/0.749/0.25 | **0.860** | 0.949 |
| Thu-Morning (web) | 2,143 | 0.007/0.05/0.012/0.10 | 0.052/0.90/0.098/0.23 | 0.034 | 0.768 |
| Thu-Afternoon (infil) | 36 | 0.001/0.89/0.003/0.09 | 0.001/0.92/0.001/0.22 | 0.003 | 0.930 |
| Friday-Morning | 1,953 | 0.021/0.21/0.038/0.11 | 0.014/0.29/0.026/0.24 | 0.018 | 0.648 |
| Friday-PortScan | 90,255 | 0.057/0.008/0.014/0.11 | 0.249/0.10/0.145/0.24 | 0.507 | 0.695 |
| Friday-DDoS | 128,013 | 0.69/0.67/**0.681**/0.42 | 0.71/0.85/0.774/0.50 | 0.654 | 0.697 |
| Val (Tue, descriptive) | 9,152 | 0.00/0.00/0.00/0.11 | 0.067/0.75/0.123/0.23 | 0.040 | 0.734 |

## 5. Attack-family and false-positive analysis

- **Volumetric floods rank well:** Wednesday (mixed DoS) and DDoS are the
  only strong days at both OPs. PortScan (90k samples, the largest attack
  mass) is nearly invisible to OP-A (R=0.008) and weak at OP-B (0.10) —
  behavioral features without port-correlated separation miss slow scans.
- **Web attacks need OP-B:** Brute-Force 0.052→0.875, XSS 0.032→0.960,
  SQLi n=21 →0.571. OP-A's Monday-calibrated offset does not transfer
  across days for low-rate attacks.
- **Infiltration n=36:** OP-A 32/36, OP-B 33/36 — matches the experiment
  record; tiny-n, report with care.
- **Benign FPR is day-dependent:** OP-A 0.09–0.13 except DDoS-day 0.42;
  OP-B roughly doubles each (DDoS-day 0.50). Friday traffic differs
  materially from Monday training.
- **Score overlap:** threshold sits in a crowded band (e.g. Wednesday TN99
  0.517 < OP-A < TP50 0.624, but FN99 0.520 and FP50 0.566 interleave) —
  no clean separation; expected for unsupervised anomaly scores.
- **ROC-AUC misleads under imbalance:** Thu-Afternoon ROC-AUC 0.93 with
  PR-AUC 0.003 (36 attacks in 241,859 rows). PR-AUC is the honest
  threshold-free summary here.

## 6. Leakage and generalization limits (descriptive, not independent)

- Global label-conflict removal + deduplication ran before splitting: test
  rows duplicating training rows were removed (documented curation; removes
  near-duplicate leakage at the cost of an idealized test set).
- Monday-benign-only training; contamination grid + OP-B sweep consumed
  Tuesday → Tuesday metrics are selection-touched (descriptive).
- Same 2017 lab capture for all splits: shared collection artifacts,
  temporal proximity, synthetic attack schedules. No evidence of
  train/test-day leakage beyond the documented pipeline, but none of this
  transfers to live traffic: aged, synthetic, imbalanced, single-network data.
- **No production-accuracy claim is supported.** These numbers describe
  CICIDS2017 behavior of the frozen detector.

## 7. Reproducibility

Chunk-size self-check (50k vs 200k) identical on every split; per-day OP-A
metrics match the original pipeline record to 4 decimals on all 6 test
days; `verify_reproducibility.py` 12/12 (P1-1); `test_ml_consistency`
API==pipeline. Rerun: `python scripts/evaluate_detector.py` (deterministic;
refuses non-empty output dir).

## 8. Operational implications

- OP-A as served misses PortScan/web-attack patterns seen on later days;
  OP-B recovers recall at ~2× FPR. Neither is "better" — the trade-off is
  now quantified per day for operators.
- DDoS-day benign FPR (0.42 OP-A) means alert volume is day-dependent;
  capacity planning cannot use a single FPR.
- Score-threshold tuning on new data is explicitly out of scope (frozen).

## 9. Future evaluation work

Independent capture evaluation with disjoint collection (acceptance: no
shared preprocessing/selection lineage); per-family calibration research
(not implementation); drift monitoring across days; larger-n infiltration
coverage. See DI-005.
