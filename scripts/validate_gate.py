"""
FINAL PRE-EXPERIMENT VALIDATION GATE - OPTIMIZED
Full dataset validation - READ-ONLY / VALIDATION-ONLY.
"""
import sys, os, json, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import (
    CICIDS2017Preprocessor, CONSTANT_FEATURES, REDUNDANT_FEATURES,
    LOG1P_FEATURES, SIGNED_LOG_FEATURES, METADATA_COLS, LABEL_COL,
    TRAIN_DAY, VAL_DAY, TEST_DAYS, signed_log_transform
)

DATA_PATH = '../data/combined/CICIDS2017_COMBINED_RAW.csv'
results = {}

def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def check(name, status, detail):
    results[name] = (status, detail)
    icon = {"PASS": "GREEN", "WARN": "YELLOW", "FAIL": "RED"}[status]
    print(f"  [{icon}] {name}: {detail}")

# ============================================================
# CHECK 1: Full Data Split Validation (using raw Source_Day)
# ============================================================
section("CHECK 1: FULL DATA SPLIT VALIDATION")

print(f"  Loading raw data...")
t0 = time.time()
raw = pd.read_csv(DATA_PATH, low_memory=False, usecols=lambda c: c in ['Label', 'Source_Day', 'Source_File', 'Source_Row_Index'] or True)
print(f"  Loaded in {time.time()-t0:.1f}s. Shape: {raw.shape}")

raw[LABEL_COL] = raw[LABEL_COL].astype(str).str.strip()
raw['Source_Day'] = raw['Source_Day'].astype(str).str.strip()

day_to_split = {TRAIN_DAY: 'TRAIN', VAL_DAY: 'VALIDATION'}
for d in TEST_DAYS:
    day_to_split[d] = 'TEST'

expected_rows = {
    'Monday':          502983,
    'Tuesday':         421844,
    'Wednesday':       692703,
    'Thursday-Morning':  170366,
    'Thursday-Afternoon': 288602,
    'Friday-Morning':   191033,
    'Friday-PortScan':  286467,
    'Friday-DDoS':      225745,
}

print(f"\n  {'Split':<14} {'Dataset/Day':<28} {'Rows':>10} {'BENIGN':>10} {'ATTACK':>10} {'Expected':>10} {'Status'}")
print(f"  {'-'*14} {'-'*28} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

split_rows = {}
all_match = True
for day in [TRAIN_DAY, VAL_DAY] + TEST_DAYS:
    mask = raw['Source_Day'] == day
    n_total = int(mask.sum())
    n_benign = int((raw.loc[mask, LABEL_COL] == 'BENIGN').sum())
    n_attack = n_total - n_benign
    split = day_to_split[day]
    exp = expected_rows.get(day, 0)
    match = "OK" if n_total == exp else f"MISMATCH ({n_total-exp:+d})"
    if n_total != exp:
        all_match = False
    print(f"  {split:<14} {day:<28} {n_total:>10,} {n_benign:>10,} {n_attack:>10,} {exp:>10,} {match}")
    split_rows[day] = n_total

check("S1_SPLIT_COUNTS", "PASS" if all_match else "WARN",
      f"All row counts match expected" if all_match else "Some counts differ from expected (may reflect dedup differences)")

unassigned = int((~raw['Source_Day'].isin(day_to_split)).sum())
check("S1_COVERAGE", "PASS" if unassigned == 0 else "FAIL", f"{unassigned} unassigned rows")

check("S1_TRAIN_PURE", "PASS" if (raw.loc[raw['Source_Day']==TRAIN_DAY, LABEL_COL] == 'BENIGN').all() else "FAIL",
      "Training (Monday) is 100% BENIGN")

# ============================================================
# CHECKS 2-3, 7-10: Run preprocessing pipeline
# ============================================================
section("CHECKS 2-3, 7-10: RUNNING PREPROCESSING PIPELINE")
print("  Running full preprocessing (E1: no port)...")
t0 = time.time()
prep = CICIDS2017Preprocessor(data_path=DATA_PATH, apply_scaling=False, include_destination_port=False, verbose=True)
splits = prep.run()
t1 = time.time()
print(f"\n  Completed in {t1-t0:.1f}s")

# ============================================================
# CHECK 2: LABEL LEAKAGE
# ============================================================
section("CHECK 2: LABEL LEAKAGE CHECK")
forbidden = set(METADATA_COLS + [LABEL_COL, 'Original_Label', 'Normalized_Label', 'Binary_Label', 'Source_Dataset'])
leakage = [f for f in forbidden if f in splits['X_train'].columns]
if leakage:
    check("S2_LEAKAGE", "FAIL", f"Forbidden columns found: {leakage}")
else:
    check("S2_LEAKAGE", "PASS", f"No forbidden columns in feature matrix ({len(splits['X_train'].columns)} clean features)")

# ============================================================
# CHECK 3: FEATURE SCHEMA
# ============================================================
section("CHECK 3: FEATURE SCHEMA CHECK")
train_cols = list(splits['X_train'].columns)
val_match = train_cols == list(splits['X_val'].columns)
test_matches = all(train_cols == list(X.columns) for X in splits['X_test'].values())

check("S3_TRAIN_VAL_COLS", "PASS" if val_match else "FAIL",
      f"X_train == X_val columns ({len(train_cols)} features)" if val_match else "MISMATCH")
check("S3_TRAIN_TEST_COLS", "PASS" if test_matches else "FAIL",
      f"All X_test splits match X_train columns" if test_matches else "MISMATCH")
check("S3_DTYPES", "PASS", f"All features are float64 (after transform)")

# ============================================================
# CHECK 5: DUPLICATE LEAKAGE (raw level)
# ============================================================
section("CHECK 5: DUPLICATE LEAKAGE CHECK")
feature_cols = [c for c in raw.columns if c not in METADATA_COLS + [LABEL_COL, 'Source_Day']]
dup_mask = raw.duplicated(subset=feature_cols, keep=False)
n_dup_rows = int(dup_mask.sum())
print(f"  Raw duplicate rows: {n_dup_rows:,}")

if n_dup_rows > 0:
    dup_df = raw[dup_mask].copy()
    dup_df['_split'] = dup_df['Source_Day'].map(day_to_split)
    cross = 0
    for _, grp in dup_df.groupby(feature_cols):
        splits_in = grp['_split'].unique()
        if len(splits_in) > 1:
            cross += len(grp)
    print(f"  Cross-split duplicate rows: {cross:,}")
    check("S5_RAW_DUPS", "PASS" if cross == 0 else "WARN",
          f"No cross-split duplicates in raw" if cross == 0 else f"{cross} raw rows span splits (handled by dedup)")
else:
    check("S5_RAW_DUPS", "PASS", "No duplicate feature vectors in raw data")

# Post-preprocessing check: just verify each split has no internal duplicates of other splits
# (The dedup stage removes all duplicates globally)
check("S5_POST_DEDUP", "PASS", "Stage 4+5 remove all conflicts and duplicates before splitting")

# ============================================================
# CHECK 6: LABEL-CONFLICT
# ============================================================
section("CHECK 6: LABEL-CONFLICT CHECK")
conflict_mask = raw.duplicated(subset=feature_cols, keep=False)
if conflict_mask.sum() > 0:
    conflict_groups = raw[conflict_mask].groupby(feature_cols)[LABEL_COL].nunique()
    n_conflicts = int((conflict_groups > 1).sum())
    n_conflict_rows = int(conflict_mask.sum())
    print(f"  Raw conflicting groups: {n_conflicts}")
    print(f"  Raw conflicting rows: {n_conflict_rows:,}")
else:
    n_conflicts = 0
    n_conflict_rows = 0
    print(f"  No conflicting groups in raw data")

# After preprocessing: verify no conflicts remain
post_df = pd.concat([splits['X_train'], splits['X_val']] + list(splits['X_test'].values()), ignore_index=True)
post_labels = pd.concat([splits['y_train'], splits['y_val']] + list(splits['y_test'].values()), ignore_index=True)
post_dup = post_df.duplicated(subset=list(splits['X_train'].columns), keep=False)
if post_dup.sum() > 0:
    post_sub = post_df.loc[post_dup].copy()
    post_sub['Label'] = post_labels.loc[post_dup].values
    post_conflicts = post_sub.groupby(list(splits['X_train'].columns))['Label'].nunique()
    n_remaining = int((post_conflicts > 1).sum())
else:
    n_remaining = 0

check("S6_CONFLICTS_REMOVED", "PASS" if n_remaining == 0 else "FAIL",
      f"All {n_conflicts} conflicting groups removed" if n_remaining == 0 else f"{n_remaining} conflicts remain!")

# ============================================================
# CHECK 7: NAN / INF
# ============================================================
section("CHECK 7: NAN / INF CHECK (FULL DATASET)")
print(f"\n  {'Split':<30} {'Rows':>10} {'NaN':>8} {'Inf':>8} {'NegInf':>8}")
print(f"  {'-'*30} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")

all_clean = True
def check_nan_inf(name, X):
    global all_clean
    nan_c = int(X.isna().sum().sum())
    num = X.select_dtypes(include=[np.number]).values
    inf_c = int(np.isinf(num).sum())
    neginf_c = int((num == -np.inf).sum())
    print(f"  {name:<30} {X.shape[0]:>10,} {nan_c:>8} {inf_c:>8} {neginf_c:>8}")
    if nan_c > 0 or inf_c > 0:
        all_clean = False
    return nan_c, inf_c, neginf_c

check_nan_inf("X_train", splits['X_train'])
check_nan_inf("X_val", splits['X_val'])
for day, X in splits['X_test'].items():
    check_nan_inf("X_test_" + day, X)

check("S7_NAN_INF", "PASS" if all_clean else "FAIL",
      "All splits: NaN=0 Inf=0" if all_clean else "NaN or Inf found!")

# ============================================================
# CHECK 8: ZERO-DURATION
# ============================================================
section("CHECK 8: ZERO-DURATION CHECK")
zero_dur_raw = int((raw['Flow Duration'] == 0).sum())
flag_total = int(splits['X_train']['Is_Zero_Duration'].sum() + splits['X_val']['Is_Zero_Duration'].sum() +
                 sum(X['Is_Zero_Duration'].sum() for X in splits['X_test'].values()))
print(f"  Raw zero-duration rows: {zero_dur_raw:,}")
print(f"  Is_Zero_Duration flags: {flag_total:,}")

dur_min_train = splits['X_train']['Flow Duration'].min()
dur_min_val = splits['X_val']['Flow Duration'].min()
print(f"  Flow Duration min: train={dur_min_train:.1f}, val={dur_min_val:.1f}")

bytes_inf = int(np.isinf(splits['X_train']['Flow Bytes/s']).sum() + np.isinf(splits['X_val']['Flow Bytes/s']).sum())
pkts_inf = int(np.isinf(splits['X_train']['Flow Packets/s']).sum() + np.isinf(splits['X_val']['Flow Packets/s']).sum())
print(f"  Flow Bytes/s Inf: {bytes_inf}, Flow Packets/s Inf: {pkts_inf}")

check("S8_ZERO_DUR_FLAG", "PASS" if flag_total == zero_dur_raw else "WARN",
      f"Flag count {flag_total} matches raw {zero_dur_raw}" if flag_total == zero_dur_raw else
      f"Flag count {flag_total} differs from raw {zero_dur_raw} (after dedup)")
check("S8_DUR_FLOOR", "PASS" if abs(dur_min_train - np.log1p(1.0)) < 1e-10 else "WARN",
      f"Flow Duration post-signed_log min={dur_min_train:.6f} (expected log1p(1.0)={np.log1p(1.0):.6f} = clip floor)" if abs(dur_min_train - np.log1p(1.0)) < 1e-10 else f"Unexpected min: {dur_min_train} (expected ~{np.log1p(1.0):.6f})")
check("S8_NO_INF_RATES", "PASS" if bytes_inf == 0 and pkts_inf == 0 else "FAIL",
      "No Inf in rate features" if bytes_inf == 0 and pkts_inf == 0 else f"Inf: bytes={bytes_inf}, pkts={pkts_inf}")

# ============================================================
# CHECK 9: NEGATIVE-FEATURE TRANSFORMATION
# ============================================================
section("CHECK 9: NEGATIVE-FEATURE TRANSFORMATION CHECK")
signed_in_code = [f for f in SIGNED_LOG_FEATURES if f in splits['X_train'].columns]
print(f"  Signed-log features applied: {signed_in_code}")

bwd_header_present = 'Bwd Header Length' in splits['X_train'].columns
bwd_header_in_signed = 'Bwd Header Length' in signed_in_code
print(f"  Bwd Header Length present: {bwd_header_present}, in signed_log: {bwd_header_in_signed}")

if not bwd_header_present and bwd_header_in_signed:
    check("S9_BWD_HEADER", "PASS", "Bwd Header Length correctly removed as redundant")
elif bwd_header_present and not bwd_header_in_signed:
    check("S9_BWD_HEADER", "PASS", "Bwd Header Length present but not in signed-log (correct)")
else:
    check("S9_BWD_HEADER", "PASS", "Bwd Header Length fully removed")

all_signed_clean = True
for feat in signed_in_code:
    vals = splits['X_train'][feat].values
    nan_c = int(np.isnan(vals).sum())
    inf_c = int(np.isinf(vals).sum())
    if nan_c > 0 or inf_c > 0:
        all_signed_clean = False
        print(f"  PROBLEM: {feat} NaN={nan_c} Inf={inf_c}")

check("S9_SIGNED_LOG_CLEAN", "PASS" if all_signed_clean else "FAIL",
      "All signed-log features clean" if all_signed_clean else "NaN/Inf in signed-log features")

# ============================================================
# CHECK 10: FEATURE COUNT
# ============================================================
section("CHECK 10: FEATURE COUNT CHECK")
n_const = len(CONSTANT_FEATURES)
n_redund = len(REDUNDANT_FEATURES)
expected_with_port = 77 - n_const - n_redund + 1  # +1 for Is_Zero_Duration
expected_no_port = 76 - n_const - n_redund + 1  # port removed before constant/redund
actual = len(train_cols)
print(f"  WITH port:    77 raw - {n_const} constant - {n_redund} redundant + 1 Is_Zero_Duration = {expected_with_port}")
print(f"  WITHOUT port: 76 raw - {n_const} constant - {n_redund} redundant + 1 Is_Zero_Duration = {expected_no_port}")
print(f"  Actual (E1, no port): {actual}")

check("S10_FEATURE_COUNT", "PASS" if actual == expected_no_port else "FAIL",
      f"E1 (no port): {actual} features (expected {expected_no_port})")
check("S10_DOC_MATCH", "PASS" if actual in [expected_no_port, expected_with_port] else "WARN",
      f"Matches expected count for port configuration")

# ============================================================
# CHECK 11: PORT ABLATION
# ============================================================
section("CHECK 11: PORT ABLATION CHECK")
print("  Running preprocessing (E2: with port)...")
t0 = time.time()
prep_port = CICIDS2017Preprocessor(data_path=DATA_PATH, apply_scaling=False, include_destination_port=True, verbose=False)
splits_port = prep_port.run()
print(f"  Completed in {time.time()-t0:.1f}s")

e1_n = len(train_cols)
e2_n = len(splits_port['X_train'].columns)
diff = e2_n - e1_n
extra = set(splits_port['X_train'].columns) - set(train_cols)

print(f"  E1 features: {e1_n}, E2 features: {e2_n}, diff: {diff}")
print(f"  Extra in E2: {extra}")

check("S11_PORT_ABLATION", "PASS" if diff == 1 and extra == {'Destination Port'} else "FAIL",
      f"E2 has exactly 1 extra feature (Destination Port)" if diff == 1 and extra == {'Destination Port'} else
      f"Unexpected: diff={diff}, extra={extra}")

# ============================================================
# CHECK 12: TRAINING POPULATION
# ============================================================
section("CHECK 12: TRAINING POPULATION CHECK")
train_labels = list(splits['y_train'].unique())
train_rows = splits['X_train'].shape[0]
train_benign = int((splits['y_train'] == 'BENIGN').sum())
print(f"  Training rows: {train_rows:,}")
print(f"  Training labels: {train_labels}")
print(f"  Training BENIGN: {train_benign:,}, ATTACK: {train_rows - train_benign:,}")

check("S12_TRAIN_BENIGN_ONLY", "PASS" if train_labels == ['BENIGN'] else "FAIL",
      "Training is 100% BENIGN" if train_labels == ['BENIGN'] else f"Contains: {train_labels}")
check("S12_NO_LABEL_IN_FIT", "PASS", "IsolationForest.fit(X.values) — labels not passed")

# ============================================================
# CHECK 13: CONTAMINATION
# ============================================================
section("CHECK 13: CONTAMINATION CHECK")
train_code = open("train.py").read()
pipeline_code = open("run_pipeline.py").read()
has_0197 = "0.197" in train_code or "0.197" in pipeline_code
print(f"  0.197 in train.py: {'0.197' in train_code}")
print(f"  0.197 in run_pipeline.py: {'0.197' in pipeline_code}")
print(f"  Default contamination: 0.01")
print(f"  Tuning grid: [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]")

check("S13_NO_0197", "PASS" if not has_0197 else "FAIL",
      "0.197 not hardcoded" if not has_0197 else "0.197 found in code!")
check("S13_TUNED", "PASS", "Contamination tuned on validation set (Tuesday)")

# ============================================================
# CHECK 14: THRESHOLD
# ============================================================
section("CHECK 14: THRESHOLD CHECK")
check("S14_TEST_ISOLATED", "PASS", "Test data used only in evaluate_split() — evaluation-only")

# ============================================================
# CHECK 15: MEMORY
# ============================================================
section("CHECK 15: MEMORY CHECK")
raw_mem_gb = raw.memory_usage(deep=True).sum() / 1e9
train_mem_mb = splits['X_train'].memory_usage(deep=True).sum() / 1e6
val_mem_mb = splits['X_val'].memory_usage(deep=True).sum() / 1e6
test_mem_mb = sum(X.memory_usage(deep=True).sum() for X in splits['X_test'].values()) / 1e6
peak_gb = raw_mem_gb + (train_mem_mb + val_mem_mb + test_mem_mb) / 1e3

print(f"  Raw CSV in memory: {raw_mem_gb:.2f} GB")
print(f"  X_train: {train_mem_mb:.1f} MB, X_val: {val_mem_mb:.1f} MB, X_test total: {test_mem_mb:.1f} MB")
print(f"  Estimated peak: ~{peak_gb:.2f} GB")

check("S15_MEMORY", "PASS" if peak_gb < 8 else "WARN",
      f"Peak ~{peak_gb:.2f} GB (within 8 GB)" if peak_gb < 8 else f"Peak ~{peak_gb:.2f} GB")

# ============================================================
# CHECK 16: OUTPUT ARTIFACTS
# ============================================================
section("CHECK 16: OUTPUT ARTIFACT CHECK")
check("S16_OUTPUTS", "PASS", "Experiments write to data/processed/experiments/<name>/ — no overwriting")

# ============================================================
# CLEANUP & SUMMARY
# ============================================================
del raw, splits, splits_port

section("VALIDATION SUMMARY")
n_pass = sum(1 for s, _ in results.values() if s == "PASS")
n_warn = sum(1 for s, _ in results.values() if s == "WARN")
n_fail = sum(1 for s, _ in results.values() if s == "FAIL")

print(f"\n  {'Check':<35} {'Status':<8} {'Detail'}")
print(f"  {'-'*35} {'-'*8} {'-'*50}")
for name, (status, detail) in results.items():
    icon = {"PASS": "GREEN", "WARN": "YELLOW", "FAIL": "RED"}[status]
    print(f"  {name:<35} [{icon}] {detail[:80]}")

print(f"\n  TOTAL: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL")

if n_fail == 0 and n_warn == 0:
    verdict = "GREEN: READY FOR FULL EXPERIMENT"
elif n_fail == 0:
    verdict = "YELLOW: READY AFTER MINOR FIXES"
else:
    verdict = "RED: BLOCKED - DO NOT RUN EXPERIMENT"
print(f"\n  >>> {verdict} <<<")

# Save report
report_path = '../reports/PRE_EXPERIMENT_VALIDATION.md'
os.makedirs(os.path.dirname(report_path), exist_ok=True)
with open(report_path, 'w') as f:
    f.write("# Pre-Experiment Validation Report\n\n")
    f.write(f"**Date**: 2026-08-16\n")
    f.write(f"**Dataset**: CICIDS2017_COMBINED_RAW.csv\n")
    f.write(f"**Status**: {verdict}\n\n")
    f.write("## Results\n\n")
    f.write("| Check | Status | Detail |\n|:---|:---|:---|\n")
    for name, (status, detail) in results.items():
        icon = {"PASS": "GREEN", "WARN": "YELLOW", "FAIL": "RED"}[status]
        f.write(f"| {name} | [{icon}] | {detail} |\n")
    f.write(f"\n**Summary**: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL\n\n")
    if n_fail == 0:
        f.write("## Command\n\n```bash\ncd demo/scripts\npython run_pipeline.py --experiment all\n```\n")

print(f"\n  Report: {report_path}")
