# CICIDS2017 Zero-Duration / Infinity Strategy — Final Audit

## 1. Executive Summary

The combined dataset contains **2,867 zero-duration flows** that produce **infinite values** in rate features and **NaN values** in `Flow Bytes/s`. This audit challenges the proposed 1 μs epsilon convention and evaluates alternatives.

---

## 2. Verified Evidence

### 2.1 Zero-Duration Flow Profile

| Metric | Value |
|:---|---:|
| Total zero-duration flows | 2,867 |
| Flow Packets/s Inf | 2,867 (100%) |
| Flow Bytes/s Inf | 1,509 (52.6%) |
| Flow Bytes/s NaN | 1,358 (47.4%) |
| NaN AND Inf co-occurrence | 1,358 |

### 2.2 Root Cause

- **Inf in Flow Packets/s**: `Total Packets / (Flow Duration × 10⁻⁶)` when Duration = 0 → division by zero.
- **Inf in Flow Bytes/s**: `Total Bytes / (Flow Duration × 10⁻⁶)` when Duration = 0 AND Total Bytes > 0 → 1,509 rows.
- **NaN in Flow Bytes/s**: `0 / 0` when Duration = 0 AND Total Bytes = 0 → 1,358 rows. The NaN is mathematically a `0/0` indeterminate form, not missing data.

### 2.3 Label Distribution

| Label | Count | Percentage |
|:---|---:|---:|
| BENIGN | 1,777 | 61.98% |
| DoS Hulk | 949 | 33.10% |
| PortScan | 126 | 4.39% |
| Bot | 10 | 0.35% |
| FTP-Patator | 3 | 0.10% |
| DDoS | 2 | 0.07% |

**Key insight**: Zero-duration flows are NOT attack-exclusive. 62% are benign. Dropping them would remove legitimate traffic.

### 2.4 Source Day Distribution

| Source Day | Count |
|:---|---:|
| Wednesday | 1,297 |
| Monday | 437 |
| Friday-PortScan | 371 |
| Tuesday | 264 |
| Thursday-Afternoon | 207 |
| Thursday-Morning | 135 |
| Friday-Morning | 122 |
| Friday-DDoS | 34 |

### 2.5 NaN Label Distribution

| Label | NaN Count |
|:---|---:|
| DoS Hulk | 949 |
| BENIGN | 409 |

ALL 1,358 NaN rows have Flow Duration = 0 AND Total Bytes = 0 (0/0 case).

---

## 3. Strategy Evaluation

### Strategy A: 1 μs Epsilon Convention (Original Proposal)
- **Concept**: `Flow Duration = max(Flow Duration, 1)`, then recompute rates.
- **Mathematical validity**: Deterministic. Produces finite, bounded rate values. CICFlowMeter's native resolution is 1 μs, so this represents the physical timing floor.
- **Information preservation**: Original Duration=0 information is lost.
- **Model implications**: The resulting rates (e.g., Packets × 10⁶ per second) are extreme but finite. Tree-based models can learn these thresholds.
- **Flaw**: Silent modification. No explicit signal to the model that these flows had zero duration.
- **Verdict**: **PARTIAL** — Mathematically valid but incomplete.

### Strategy B: Zero_Duration_Flag + 1 μs Epsilon (RECOMMENDED)
- **Concept**: 
  1. Create `Is_Zero_Duration = (Flow Duration == 0).astype(int)`
  2. Set `Flow Duration = max(Flow Duration, 1.0)` for rate computation
  3. Recompute `Flow Bytes/s` and `Flow Packets/s` deterministically
- **Mathematical validity**: Deterministic and reproducible.
- **Information preservation**: Preserves the zero-duration semantics via the binary flag while enabling stable rate computation.
- **Model implications**: Isolation Forest can use the binary flag to isolate zero-duration flows at the first split, then use the extreme rates as secondary discrimination.
- **Advantage**: Gives the model explicit information about the physical timing anomaly without losing rate information.
- **Verdict**: **APPROVED** — Best balance of mathematical validity and information preservation.

### Strategy C: Drop Rate Features
- **Concept**: Drop `Flow Bytes/s` and `Flow Packets/s` entirely.
- **Flaw**: These are among the most informative features for volumetric attack detection (DDoS, DoS Hulk, PortScan). Dropping them cripples detection of the most common attacks.
- **Verdict**: **REJECTED** — Unacceptable information loss.

### Strategy D: Exclude Zero-Duration Rows
- **Concept**: Drop all 2,867 zero-duration flows.
- **Flaw**: Removes 62% benign flows. Distorts the benign distribution. Reduces dataset by 0.1% (small but unnecessary).
- **Verdict**: **REJECTED** — Unnecessary data loss when deterministic imputation is available.

---

## 4. NaN Handling Strategy

The 1,358 NaN values in `Flow Bytes/s` are NOT missing data — they are `0/0` indeterminate forms.

**Resolution**:
- When `Flow Duration == 0` AND `Total Bytes == 0`: Set `Flow Bytes/s = 0.0` (zero bytes in zero time = zero rate).
- This is mathematically defensible: if no bytes were transmitted, the byte rate is zero regardless of duration.

**Alternative**: After setting `Flow Duration = max(Flow Duration, 1.0)`, recompute `Flow Bytes/s = Total Bytes / (Flow Duration × 10⁻⁶)`. Since `Total Bytes = 0`, this also yields `Flow Bytes/s = 0.0`.

Both approaches produce the same result. The recomputation approach is more consistent.

---

## 5. Recomputation Formula

For zero-duration flows:
```
Flow Duration_imputed = max(Flow Duration, 1.0)
Flow Bytes/s_imputed = Total Bytes / (Flow Duration_imputed × 10⁻⁶)
Flow Packets/s_imputed = Total Packets / (Flow Duration_imputed × 10⁻⁶)
```

For the 1,358 NaN cases (Total Bytes = 0):
```
Flow Bytes/s_imputed = 0 / (1.0 × 10⁻⁶) = 0.0
```

For the 1,509 Inf cases (Total Bytes > 0):
```
Flow Bytes/s_imputed = Total Bytes / (1.0 × 10⁻⁶) = Total Bytes × 10⁶
```

---

## 6. Final Recommendation

| Decision | Verdict | Reason |
|:---|:---|:---|
| Add `Is_Zero_Duration` flag | **APPROVED** | Explicit semantic signal for tree splits |
| Set `Flow Duration = max(Flow Duration, 1.0)` | **APPROVED** | Deterministic, physically bounded |
| Recompute rate features from imputed duration | **APPROVED** | Mathematically consistent |
| Set NaN `Flow Bytes/s` = recomputed value (0.0) | **APPROVED** | Resolves 0/0 indeterminate form |
| Drop zero-duration rows | **REJECTED** | 62% are benign; unnecessary data loss |
| Drop rate features | **REJECTED** | Critical for volumetric attack detection |
