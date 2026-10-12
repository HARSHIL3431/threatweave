#!/usr/bin/env python3
"""Frozen E2 detector evaluation (P1-8, evaluation-only).

Recomputes confusion metrics from the saved pipeline scores/labels at the
two frozen thresholds. Deterministic, offline, read-only: never trains,
retunes, regenerates, or overwrites model artifacts, prior reports, or
baselines. Writes a new versioned output directory only.

Usage (from the repository root):
    python scripts/evaluate_detector.py
    python scripts/evaluate_detector.py --out data/processed/analysis/detector_eval_p18
"""
import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.detector_evaluation import normalize_label  # noqa: E402

SCRIPT_VERSION = "evaluate_detector.py v1 (P1-8)"

DAY_FILES = [
    ("Wednesday", "Wednesday"),
    ("Thursday-Morning", "Thursday_Morning"),
    ("Thursday-Afternoon", "Thursday_Afternoon"),
    ("Friday-Morning", "Friday_Morning"),
    ("Friday-PortScan", "Friday_PortScan"),
    ("Friday-DDoS", "Friday_DDoS"),
]
RAW_CSVS = [
    "dataset/Monday-WorkingHours.pcap_ISCX.csv",
    "dataset/Tuesday-WorkingHours.pcap_ISCX.csv",
    "dataset/Wednesday-workingHours.pcap_ISCX.csv",
    "dataset/Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv",
    "dataset/Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv",
    "dataset/Friday-WorkingHours-Morning.pcap_ISCX.csv",
    "dataset/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv",
    "dataset/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv",
]
QUANTILES = (0.5, 0.9, 0.99)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_day(exp_dir: Path, stem: str):
    """Load saved scores + labels; fail loudly on length mismatch."""
    import numpy as np
    import pandas as pd

    scores = np.load(exp_dir / "scores" / f"{stem}_scores.npy")
    labels_raw = pd.read_csv(exp_dir / "scores" / f"{stem}_labels.csv")["Label"]
    labels = [normalize_label(v) for v in labels_raw.tolist()]
    excluded = sum(1 for lab in labels if lab is None)
    kept = [(float(s), lab) for s, lab in zip(scores.tolist(), labels) if lab is not None]
    if len(scores) != len(labels_raw):
        raise ValueError(f"{stem}: scores ({len(scores)}) != labels ({len(labels_raw)})")
    return kept, excluded


def main() -> None:
    from app.services.detector_evaluation import (
        BENIGN_LABEL,
        E2_EXPERIMENT,
        E2_FEATURE_COUNT,
        OP_A_THRESHOLD,
        OP_B_THRESHOLD,
        accumulate_confusion,
        attack_recall,
        chunked_confusion,
        confusion_at_threshold,
    )

    parser = argparse.ArgumentParser(description="Frozen E2 detector evaluation")
    parser.add_argument("--out", type=Path,
                        default=REPO_ROOT / "data" / "processed" / "analysis" / "detector_eval_p18")
    parser.add_argument("--chunk-sizes", type=int, nargs=2, default=[50000, 200000])
    args = parser.parse_args()

    exp_dir = REPO_ROOT / "data" / "processed" / "experiments" / "with_port"
    print("P1-8 frozen-detector evaluation (read-only, no retraining)")

    # Frozen-threshold cross-check against the experiment record.
    recorded = json.loads((exp_dir / "results.json").read_text(encoding="utf-8"))
    assert recorded["config"]["frozen_threshold"] == OP_A_THRESHOLD, "OP-A drift!"
    assert recorded["experiment_name"] == E2_EXPERIMENT
    print(f"Thresholds verified: OP-A={OP_A_THRESHOLD}, OP-B={OP_B_THRESHOLD}")

    try:
        from sklearn.metrics import average_precision_score, roc_auc_score
        have_sklearn = True
    except ImportError:
        have_sklearn = False
        print("WARNING: scikit-learn unavailable; PR/ROC-AUC will be undefined")

    per_day = []
    attack_rows = []
    pooled = {"OP-A": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
              "OP-B": {"tp": 0, "fp": 0, "tn": 0, "fn": 0}}
    total_excluded = 0

    for day, stem in [("Validation (Tuesday)", "val")] + DAY_FILES:
        kept, excluded = load_day(exp_dir, stem)
        total_excluded += excluded
        scores = [s for s, _ in kept]
        labels = [lab for _, lab in kept]
        vocab = sorted(set(labels))
        n_benign = sum(1 for lab in labels if lab == BENIGN_LABEL)

        # Chunked self-check with two chunk sizes (order-independent sums).
        for chunk_size in args.chunk_sizes:
            chunks_s = [scores[i:i + chunk_size] for i in range(0, len(scores), chunk_size)]
            chunks_l = [labels[i:i + chunk_size] for i in range(0, len(labels), chunk_size)]
            check = chunked_confusion(chunks_s, chunks_l, OP_A_THRESHOLD)
            ref = accumulate_confusion(scores, labels, OP_A_THRESHOLD)
            assert check == ref, f"{day}: chunked/reference mismatch"

        row = {"split": day, "n": len(kept), "n_benign": n_benign,
               "n_attack": len(kept) - n_benign, "excluded": excluded,
               "labels": ";".join(vocab)}
        import numpy as np

        for op, threshold in (("OP-A", OP_A_THRESHOLD), ("OP-B", OP_B_THRESHOLD)):
            conf = accumulate_confusion(scores, labels, threshold)
            metrics = confusion_at_threshold(**conf)
            for key in ("tp", "fp", "tn", "fn", "precision", "recall", "f1",
                        "fpr", "specificity", "balanced_accuracy"):
                row[f"{op}_{key}"] = metrics[key]
            for key in ("tp", "fp", "tn", "fn"):
                pooled[op][key] += conf[key]

        if have_sklearn:
            y = [1 if lab != BENIGN_LABEL else 0 for lab in labels]
            arr = np.asarray(scores, dtype=np.float64)
            if len(set(y)) == 2:
                row["pr_auc"] = float(average_precision_score(y, arr))
                row["roc_auc"] = float(roc_auc_score(y, arr))
            else:
                row["pr_auc"] = None
                row["roc_auc"] = None
        else:
            row["pr_auc"] = None
            row["roc_auc"] = None

        # Score quantiles per outcome group at OP-A (descriptive, small arrays).
        groups = {"TP": [], "FN": [], "FP": [], "TN": []}
        for score, lab in zip(scores, labels):
            pred, actual = score >= OP_A_THRESHOLD, lab != BENIGN_LABEL
            groups["TP" if pred and actual else
                   "FN" if actual else
                   "FP" if pred else "TN"].append(score)
        for group, values in groups.items():
            if values:
                quantiles = np.quantile(np.asarray(values), QUANTILES)
                row[f"q50_{group}"] = float(quantiles[0])
                row[f"q90_{group}"] = float(quantiles[1])
                row[f"q99_{group}"] = float(quantiles[2])
            else:
                row[f"q50_{group}"] = row[f"q90_{group}"] = row[f"q99_{group}"] = None
        per_day.append(row)

        for attack in sorted(set(labels) - {BENIGN_LABEL}):
            for op, threshold in (("OP-A", OP_A_THRESHOLD), ("OP-B", OP_B_THRESHOLD)):
                rec = attack_recall(scores, labels, attack, threshold)
                attack_rows.append({"split": day, "op": op, **rec})
        print(f"  {day}: n={len(kept)} benign={n_benign} excluded={excluded}")

    pooled_metrics = {
        op: confusion_at_threshold(**conf) for op, conf in pooled.items()
    }

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise SystemExit(f"FATAL: refusing to overwrite non-empty {out}")

    with open(out / "per_day.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_day[0].keys()))
        writer.writeheader()
        writer.writerows(per_day)
    with open(out / "attack_wise.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["split", "op", "attack",
                                                    "samples", "detected", "recall"])
        writer.writeheader()
        writer.writerows(attack_rows)

    print("Hashing source CSVs and frozen artifacts (read-only)...")
    manifest = {
        "script": SCRIPT_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment": E2_EXPERIMENT,
        "feature_count": E2_FEATURE_COUNT,
        "op_a_threshold": OP_A_THRESHOLD,
        "op_b_threshold": OP_B_THRESHOLD,
        "score_semantics": "-score_samples(); higher means more anomalous",
        "decision_rule": "score >= threshold",
        "positive_class": "Label != 'BENIGN' after whitespace strip",
        "dataset_hashes": {p: sha256_file(REPO_ROOT / p) for p in RAW_CSVS},
        "artifact_hashes": {
            "model.pkl": sha256_file(exp_dir / "model.pkl"),
            "preprocessing_config.json": sha256_file(exp_dir / "preprocessing_config.json"),
        },
        "total_excluded_invalid_labels": total_excluded,
    }
    metrics_doc = {
        "manifest": manifest,
        "per_day": per_day,
        "pooled": pooled_metrics,
        "attack_wise": attack_rows,
    }
    with open(out / "metrics.json", "w", encoding="utf-8") as handle:
        json.dump(metrics_doc, handle, indent=2, default=str)

    lines = ["# Frozen E2 Detector Evaluation (P1-8)",
             "",
             f"Experiment `{E2_EXPERIMENT}`, 60 features, "
             f"OP-A `{OP_A_THRESHOLD}`, OP-B `{OP_B_THRESHOLD}`.",
             "Positive class: any label other than BENIGN. "
             "Undefined metrics are null, never zero-filled.",
             "",
             "## Pooled test days (6 files; train/val excluded)",
             ""]
    for op in ("OP-A", "OP-B"):
        m = pooled_metrics[op]
        lines.append(f"### {op}")
        lines.append(f"TP={m['tp']} FP={m['fp']} TN={m['tn']} FN={m['fn']}")
        lines.append(f"precision={m['precision']} recall={m['recall']} "
                     f"F1={m['f1']} FPR={m['fpr']} "
                     f"specificity={m['specificity']} "
                     f"balanced_accuracy={m['balanced_accuracy']}")
        lines.append("")
    with open(out / "report.md", "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    with open(out / "manifest.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)

    print(f"Wrote {out} (per_day.csv, attack_wise.csv, metrics.json, report.md, manifest.json)")
    print("Pooled:", json.dumps(pooled_metrics, default=str))


if __name__ == "__main__":
    main()
