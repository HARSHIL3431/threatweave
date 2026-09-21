# CICIDS2017 Duplicate Strategy — Final Audit

## 1. Executive Summary

The combined CICIDS2017 dataset contains **2,830,743 rows** of which **309,079 are exact duplicates (10.92%)** based on all 77 feature columns. This audit presents a rigorous, evidence-based duplicate strategy that addresses train/test leakage, label conflicts, and distribution distortion.

---

## 2. Verified Duplicate Landscape

### 2.1 Quantitative Evidence (Re-verified)

| Metric | Count | Percentage |
|:---|---:|---:|
| Total rows | 2,830,743 | 100.00% |
| Duplicate rows (keep=first) | 309,079 | 10.92% |
| Unique feature vectors | 2,521,664 | 89.08% |
| Duplicate groups (>1 row) | 95,461 | — |
| Rows in duplicate groups | 403,534 | 14.25% |
| **Intra-dataset duplicates** | 196,278 | 6.93% |
| **Inter-dataset duplicates** | 111,795 | 3.95% |

### 2.2 Source of Duplicates

- **Intra-dataset**: Identical flow vectors within the same day's CSV (e.g., DoS Hulk emitting identical HTTP GET templates; PortScan sending identical 1-packet SYN probes to different ports but with identical aggregate statistics).
- **Inter-dataset**: Identical flow vectors appearing on different recording days (e.g., background DNS queries that produce the same statistical signature on Monday and Friday).

---

## 3. Label Conflict Analysis (Critical Finding)

**697 unique feature vectors possess conflicting labels.** This means the exact same 77-dimensional feature vector is labeled as both `BENIGN` and an attack type.

### 3.1 Conflict Breakdown

| Label Pair | Conflicting Feature Vectors | Total Rows Involved |
|:---|---:|---:|
| BENIGN vs PortScan | 564 | ~5,800 |
| BENIGN vs DoS Hulk | 129 | ~700 |
| BENIGN vs DDoS | 3 | ~8 |
| BENIGN vs DoS slowloris | 1 | ~2 |
| **TOTAL** | **697** | **6,666** |

### 3.2 Root Cause

Basic network operations (single SYN packets, aborted connections, background polling) produce identical CICFlowMeter feature vectors regardless of whether they are benign or attack traffic. For example:
- A benign RST packet and a PortScan SYN probe can produce the same 1-packet, 0-byte flow signature.
- A benign HTTP GET and a DoS Hulk HTTP GET template can produce identical flow statistics.

### 3.3 Implication

**Blind `df.drop_duplicates()` is dangerous.** Pandas retains the first occurrence, and the label assignment depends on arbitrary CSV loading order. This could corrupt ground truth for 6,666 rows.

---

## 4. Strategy Evaluation

### Strategy A: Delete All Exact Duplicates Before Splitting (ORIGINAL PROPOSAL)
- **Approach**: `df.drop_duplicates(subset=feature_cols, keep='first')`
- **Leakage Risk**: None (identical vectors cannot bridge train/test)
- **Flaw**: Arbitrarily resolves 697 label conflicts by file loading order. Corrupts ground truth. Distorts volumetric attack distributions where repeated identical flows are semantically meaningful (e.g., DoS Hulk repeated GET requests represent actual repeated attack traffic).
- **Verdict**: **REJECTED** — Unacceptable label corruption.

### Strategy B: Keep Duplicates with Group-Aware Splitting
- **Approach**: Assign group IDs to duplicate clusters; ensure all rows in a group go to the same split.
- **Leakage Risk**: Low if implemented correctly.
- **Flaw**: Does not resolve the 697 label conflicts. Group-aware cross-validation with 95,461 groups across 2.83M rows is computationally expensive and complex to implement correctly.
- **Verdict**: **REJECTED** — Does not address the fundamental label conflict problem.

### Strategy C: Remove Label Conflicts, Then Deduplicate (RECOMMENDED)
- **Approach**:
  1. Identify all feature vectors with >1 unique label (697 groups, 6,666 rows).
  2. Remove ALL rows in these conflicting groups.
  3. Apply `df.drop_duplicates(subset=feature_cols, keep='first')` to remaining data.
- **Leakage Risk**: None.
- **Data Loss**: 6,666 rows (0.24% of dataset) for conflicts + remaining duplicate copies.
- **Post-dedup size**: ~2,521,664 unique rows.
- **Advantage**: Guarantees 1 feature vector = 1 deterministic label. No ambiguity. No loading-order dependency. Clean ground truth.
- **Verdict**: **APPROVED** — Only scientifically defensible approach.

### Strategy D: Keep Duplicates for Distribution Analysis, Prevent Crossing
- **Approach**: Keep duplicate rows but use them only for distribution characterization; prevent duplicate groups from crossing train/test.
- **Flaw**: Still does not resolve label conflicts. Complex implementation.
- **Verdict**: **REJECTED** — Unnecessary complexity for marginal benefit.

---

## 5. Recommended Implementation

```python
# Step 1: Identify conflicting feature vectors
feature_cols = [c for c in df.columns if c not in ['Label', 'Source_File', 'Source_Day', 'Source_Row_Index']]

conflict_mask = df.duplicated(subset=feature_cols, keep=False)
conflict_groups = df[conflict_mask].groupby(feature_cols)['Label'].nunique()
conflict_features = conflict_groups[conflict_groups > 1].index

# Step 2: Remove all rows with conflicting labels
conflict_row_mask = df.set_index(feature_cols).index.isin(conflict_features)
df_clean = df[~conflict_row_mask].copy()

# Step 3: Deduplicate remaining rows
df_clean = df_clean.drop_duplicates(subset=feature_cols, keep='first')

# Result: ~2,515,000 clean rows with deterministic labeling
```

---

## 6. When Deduplication Occurs in the Pipeline

Deduplication must occur **BEFORE train/test splitting** to prevent identical feature vectors from appearing in both partitions.

**Pipeline position**:
```
RAW COMBINED DATA
    ↓
SCHEMA VALIDATION (column names, label encoding)
    ↓
CONFLICT REMOVAL (697 groups, 6,666 rows)
    ↓
DEDUPLICATION (keep=first on remaining ~2.82M rows)
    ↓
TRAIN / VALIDATION / TEST SPLIT
    ↓
...
```

---

## 7. Final Recommendation

| Decision | Evidence | Verdict |
|:---|:---|:---|
| Remove all duplicates before splitting | 309,079 duplicates (10.92%) | **APPROVED** |
| Remove label-conflicting rows first | 697 conflicting vectors, 6,666 rows | **APPROVED** |
| Use `keep='first'` after conflict removal | No conflicts remain after Step 2 | **APPROVED** |
| Dedup before train/test split | Prevents identical train/test vectors | **APPROVED** |
