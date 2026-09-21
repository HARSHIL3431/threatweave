# CICIDS2017 Preprocessing Decision Matrix

## Scientific Decision Table

Every major preprocessing decision is evaluated against evidence, leakage risk, and scientific justification.

| # | Decision | Previous Proposal | Evidence (Verified) | Verdict | Reason |
|:---|:---|:---|:---|:---|:---|
| 1 | **Duplicate removal** | `df.drop_duplicates()` before splitting | 309,079 duplicates (10.92%); 111,795 inter-dataset; 697 label conflicts (6,666 rows) | **MODIFIED** | Must remove label-conflicting rows FIRST (Strategy C), then deduplicate. Blind drop_duplicates corrupts labels for 6,666 rows. |
| 2 | **Zero-duration handling** | Set `Flow Duration = 1` | 2,867 zero-duration flows; 62% benign; 100% cause Inf; ALL NaN overlap | **MODIFIED** | Add `Is_Zero_Duration` flag before imputation. Recompute rates deterministically. Do NOT drop rows (62% benign). |
| 3 | **Inf handling** | Replace Inf via 1 μs rate | 2,867 Inf rows; 100% from Duration=0 | **APPROVED** (with Stage 8 flag) | 1 μs is the physical timing floor of CICFlowMeter. Deterministic and reproducible. |
| 4 | **NaN imputation** | Median imputation for 1,358 NaN | 1,358 NaN ALL in Flow Bytes/s; ALL overlap with zero-duration; ALL are 0/0 indeterminate forms | **MODIFIED** | NaN is resolved by zero-duration handling (Stage 8). Median imputation is fallback only. No separate imputation needed. |
| 5 | **Constant feature removal** | Drop 8 constant-zero features | 8 features verified constant zero across 2.83M rows; provide zero variance | **APPROVED** | Zero variance = zero information. Unconditional removal. |
| 6 | **Semi-constant features** | Not explicitly addressed | Fwd URG Flags (315 non-zero), CWE Flag Count (315), RST Flag Count (~670), ECE Flag Count (~670) | **MODIFIED** | Remove CWE Flag Count and ECE Flag Count (redundant with r=1.0). Evaluate Fwd URG Flags and RST Flag Count experimentally. |
| 7 | **Redundant feature removal** | Drop 10 perfectly correlated features | 23 pairs with r ≥ 0.999; 9 canonical groups identified | **MODIFIED** | Correct groupings: Bwd Header Length groups with Fwd Header Length (r=0.999), not independently. Total: 10 removals (not 10 pairs). |
| 8 | **Log transformation** | `log10(x+1)` on heavy-tailed features | 12 features have negative values; log1p undefined for x < -1; 10 features with extreme negatives (Fwd Header Length min = -32 billion) | **REJECTED** | Standard log1p is mathematically invalid for 12 features with negative values. Must use `sign(x) * log1p(|x|)` for those features, or apply only to non-negative features. |
| 9 | **RobustScaler** | Apply RobustScaler after log transform | Isolation Forest is tree-based; scaling not required for splitting | **MODIFIED** | Scaling is optional for Isolation Forest. Include for pipeline consistency with future supervised models. Fit on training data only. |
| 10 | **Destination Port** | Drop for behavioral detection | 12/14 attack types are 100% port-correlated; PortScan distributed across 1,000 ports | **EXPERIMENT REQUIRED** | Run with and without Port. Primary model: without Port (behavioral). Ablation: with Port. |
| 11 | **Source_Day as feature** | Not a model feature | P(Attack\|Day): Monday=0%, Friday-DDoS=56.7% | **REJECTED** | Source_Day is a leakage channel. If included, model learns "Friday = attack" instead of behavioral anomalies. |
| 12 | **Source_Dataset as feature** | Not a model feature | Each day's CSV = one Source_Dataset | **REJECTED** | Same as Source_Day — metadata, not behavioral signal. |
| 13 | **Labels as features** | Never | N/A | **REJECTED** | Labels are targets, never features. |
| 14 | **contamination = 0.197** | Set contamination to global attack ratio | Training on BENIGN only → true contamination = 0.0; 0.197 on benign data forces 19.7% of benign flows to be flagged as attacks | **REJECTED** | Fundamental misunderstanding of contamination parameter. Must be tuned experimentally (0.001–0.10). |
| 15 | **Training population** | Monday BENIGN (100% clean) | Monday = 529,918 benign flows, 0 attacks | **APPROVED** | Clean baseline; cross-day evaluation tests generalization. |
| 16 | **Train/test split** | Random split with `random_state=42` | Temporal burst correlation; attack concentration by day; duplicate groups spanning days | **REJECTED** | Random split creates temporal leakage. Must use source-day based splitting. |
| 17 | **Feature matrix columns** | 59 features (after removing 8 constant + 10 redundant) | Verified: 77 - 18 + 1 (Is_Zero_Duration) = 60 features; 61 with Destination Port | **MODIFIED** | 60 base features + Is_Zero_Duration = 61 total. Destination Port experimental. |
| 18 | **Negative value handling** | Not addressed | 12 features have negative values; some extreme (Fwd Header Length: -32 billion) | **NEW DECISION** | Use `sign(x) * log1p(|x|)` for features with negatives. Cannot use standard log1p. |
| 19 | **Dedup timing** | Before train/test split | Inter-dataset duplicates span days; random split would leak | **APPROVED** | Dedup must occur before any splitting. |
| 20 | **Duplicate group handling** | Not addressed | 95,461 duplicate groups | **MODIFIED** | After conflict removal, simple keep='first' is sufficient. No group-aware splitting needed since all duplicates are resolved. |

---

## Summary of Verdicts

| Verdict | Count | Decisions |
|:---|---:|:---|
| **APPROVED** | 5 | Inf handling, Constant removal, Training population, Dedup timing, Destination Port in ablation |
| **MODIFIED** | 9 | Duplicates, Zero-duration, NaN, Semi-constants, Redundants, Scaling, Feature matrix, Negative values, Duplicate groups |
| **REJECTED** | 4 | Log transform (as proposed), contamination=0.197, Random split, Source_Day/Dataset as features |
| **EXPERIMENT REQUIRED** | 1 | Destination Port inclusion |
| **NEW DECISION** | 1 | Negative value handling |
