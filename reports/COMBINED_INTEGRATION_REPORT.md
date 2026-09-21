# CICIDS2017 Final Combined Integration Report

## 1. Project Overview
This document serves as the final integration report for the **CICIDS2017 Autonomous EDA & Dataset Combination Project**.

The objective of this phase was to construct a trustworthy, controlled, and combined CICIDS2017 dataset from the 8 original day-specific PCAP-exported CSV files. The process was engineered to guarantee absolute data provenance, standardize schemas, eliminate parsing artifacts, and evaluate the combined feature matrix for machine learning readiness.

---

## 2. Integration Pipeline Audit

### Phase 1: Source Integrity Verification
- **Status:** **PASS**
- **Action:** SHA-256 checksums were calculated for all 8 original CSV files residing in `dataset/`.
- **Result:** All 8 datasets were confirmed 100% byte-identical to the baseline hashes generated prior to the initial EDA, proving that no source data was accidentally mutated.

### Phase 2: Schema Harmonization
- **Status:** **PASS**
- **Action:**
  1. Stripped whitespace from all column headers.
  2. Dropped the redundant CICFlowMeter artifact `Fwd Header Length.1` (column index 34).
  3. Stripped trailing whitespace from class labels.
  4. Repaired encoding artifacts for Thursday Web Attacks (converting U+FFFD Replacement Characters to dash delimiters).
  5. Injected explicit provenance tracing columns (`Source_File`, `Source_Day`, `Source_Row_Index`).

### Phase 3: Controlled Concatenation
- **Status:** **PASS**
- **Result:** All 8 datasets merged cleanly into a single contiguous DataFrame comprising **2,830,743 rows** and **81 columns** (78 features + 3 provenance).

### Phase 4: Combined Dataset Validation
- **Status:** **PASS**
- **Total Flow Count:** 2,830,743 (Matches sum of original 8 files).
- **Label Distribution:** 15 exact classes validated against Phase 1 global inventory.
- **Data Quality:** 2,867 `Inf` values identified (100% mapped to `Flow Duration == 0`), and 1,358 `NaN` values. 

---

## 3. Benchmark EDA Discoveries

The combined benchmark-level EDA yielded several critical insights that dictate the required preprocessing design:

### 3.1 The "Cross-Dataset Duplicate" Hazard
While individual days exhibited duplicate rates between 1% and 25%, the combined dataset contains **308,381 removable duplicate rows (10.89%)**.
Crucially, **139,843** of these rows are *inter-dataset* duplicates—meaning the exact same network flow mathematical signature occurs on entirely different days. Without suite-wide deduplication, these identical flow vectors will inevitably bridge train/test splits, leaking test labels and artificially inflating model performance metrics.

### 3.2 Label Imbalance
The dataset contains a 19.70% attack contamination ratio (557,646 attacks vs 2,273,097 benign flows).

### 3.3 Feature Matrix Redundancy
Out of the 77 available numeric features:
- **8 features are constant zero** across all 2.8 million rows.
- **10 features are perfectly correlated** ($r = 1.0000$) redundancies of other features.
- The true usable feature dimensionality is **59**.

---

## 4. Final Deliverables

The combined integration project has produced the following artifacts:

1. **Combined Raw Dataset:** `data/combined/CICIDS2017_COMBINED_RAW.csv` (1.05 GB)
2. **Dataset Manifest:** `data/combined/MANIFEST.json`
3. **Integration Code:** `scripts/combine_phase2_4_integration.py`
4. **Combined EDA Code:** `scripts/combine_phase5_eda.py`
5. **Combined EDA Visualizations:** `figures/combined_eda/`
6. **Preprocessing Specifications:** `reports/COMBINED_PREPROCESSING_DESIGN.md`

## 5. Conclusion
The combined dataset has been successfully constructed, validated, and audited. The `CICIDS2017_COMBINED_RAW.csv` dataset, along with its specific preprocessing directives, is now formally certified as **READY for Machine Learning Pipeline Development**, including Isolation Forest tuning and supervised anomaly detection benchmarking.
