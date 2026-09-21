# ML_SPLIT_STRATEGY.md

Source of truth for the train/validation/test split strategy.

---

## Split Architecture (Validated 2026-08-16)

| Split | Source Day | Rows (E1, no port) | Rows (E2, with port) | BENIGN | ATTACK | Purpose |
|:---|:---|---:|---:|:---|:---|:---|
| **Training** | Monday | 459,093 | 502,981 | 100% | 0% | Fit Isolation Forest on clean normal traffic |
| **Validation** | Tuesday | 389,405 | 421,760 | ~96.9% | ~3.1% | Tune contamination, threshold selection |
| **Test 1** | Wednesday | 573,272 | 602,393 | ~73% | ~27% | DoS detection |
| **Test 2** | Thursday-Morning | 143,093 | 156,251 | ~99% | ~1% | Web Attack detection |
| **Test 3** | Thursday-Afternoon | 190,835 | 241,859 | ~99.98% | ~0.02% | Infiltration detection |
| **Test 4** | Friday-Morning | 158,851 | 173,035 | ~99% | ~1% | Bot detection |
| **Test 5** | Friday-PortScan | 105,728 | 204,927 | ~44% | ~56% | PortScan detection |
| **Test 6** | Friday-DDoS | 213,143 | 217,761 | ~43% | ~57% | DDoS detection |

**Note**: E1 (no port) has fewer rows because removing Destination Port before dedup merges more duplicate feature vectors. This is expected and correct — the model sees the same behavioral feature space that E2 would see without port information.

---

## Why Source-Day Splitting

1. **No temporal leakage**: Each day has distinct attack types concentrated in specific time windows. Random splitting would distribute burst flows across train/test.
2. **Clean training baseline**: Monday = 100% benign. Zero attack contamination during training.
3. **Natural evaluation**: Tests whether the model generalizes from Monday's normal traffic to detect attacks on other days.
4. **Duplicate prevention**: After deduplication, no identical feature vectors span train/test.

---

## Why NOT Random Splitting

- Random `train_test_split(random_state=42)` distributes attack bursts from the same multi-minute window into both train and test.
- Creates temporal leakage: the model sees attack-day traffic patterns during training.
- Duplicate records would appear in both splits, inflating metrics.

---

## Leakage Prevention Checklist

- [ ] No duplicate feature vectors across train/test
- [ ] No labels in feature matrix
- [ ] No Source_Day in feature matrix
- [ ] No Source_File in feature matrix
- [ ] No Source_Row_Index in feature matrix
- [ ] All preprocessing fitted on training data only
- [ ] Contamination tuned on validation data only
- [ ] Final test sets evaluated exactly once
- [ ] Feature column ordering identical across all splits
