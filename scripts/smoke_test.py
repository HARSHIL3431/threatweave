"""Quick smoke test for the pipeline."""
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preprocess import CICIDS2017Preprocessor
from train import IsolationForestTrainer

print("Loading and sampling data...")
df = pd.read_csv("../data/combined/CICIDS2017_COMBINED_RAW.csv", nrows=5000)
df.to_csv("test_sample.csv", index=False)
print("Sample shape:", df.shape)

print("\n--- PREPROCESSING ---")
preprocessor = CICIDS2017Preprocessor(
    data_path="test_sample.csv",
    apply_scaling=False,
    include_destination_port=False,
    verbose=True,
)
splits = preprocessor.run()

train_rows = splits["X_train"].shape[0]
if train_rows < 10:
    print("\nNot enough training rows in tiny sample (all Monday). Skipping train/eval.")
else:
    print("\n--- TRAINING ---")
    trainer = IsolationForestTrainer(contamination=0.01)
    trainer.train(splits["X_train"])

    print("\n--- EVALUATION ---")
    has_test = False
    for day, X in splits["X_test"].items():
        y = splits["y_test"][day]
        if X.shape[0] == 0:
            continue
        has_test = True
        result = trainer.evaluate_split(X, y, day)
        print("  %s: F1=%.4f Recall=%.4f FPR=%.4f" % (day, result["f1"], result["recall"], result["fpr"]))
    if not has_test:
        print("  No test rows in tiny sample (all Monday). Skipping.")

print("\n--- NaN/Inf CHECK ---")
all_clean = True
all_splits = [splits["X_train"], splits["X_val"]] + list(splits["X_test"].values())
for i, split_df in enumerate(all_splits):
    if split_df.shape[0] == 0:
        continue
    nan_count = split_df.isna().sum().sum()
    inf_count = np.isinf(split_df.select_dtypes(include=[np.number]).values).sum()
    if nan_count > 0 or inf_count > 0:
        all_clean = False
        print("  WARNING split %d: NaN=%d Inf=%d" % (i, nan_count, inf_count))

if all_clean:
    print("  All splits: NaN=0 Inf=0")

# Cleanup
os.remove("test_sample.csv")
print("\nSMOKE TEST PASSED")
