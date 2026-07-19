"""
06c_train_relative_model.py

Trains the Relative Strength model - a separate signal from the existing
BUY (06_train_model.py) and SELL (06b_train_sell_model.py) models, not a
replacement for either.

Why a separate model: the existing BUY/SELL labels are absolute-return
thresholds ("did this trade earn >1% profit"), which is noisy because most
of a stock's 10-day return is just "did the whole market move" - largely
unpredictable from technical features. Label_10d_relative instead asks "did
this stock beat the day's average stock" (see 04_label_construction.py),
which isolates the learnable cross-sectional part of the signal.

experiments/auc_experiments.py compared this in isolation before it was
built into the real pipeline: the relative label alone lifted mean
walk-forward AUC from 0.520 to 0.540 and fixed most anti-predictive folds
(5/9 -> 2/9 with AUC < 0.5); paired with the cross-sectional rank + regime
features added in 03_feature_engineering.py, 0.550 and 0/9.

IMPORTANT - this is NOT a profit signal. A stock can "beat the market"
while still losing money in a falling market. It's served as
relative_strength, deliberately separate from buy_confidence/sell_confidence
so it can't be misread as a trade profitability claim (see
app/services/signal_service.py and app/schemas.py).

XGBoost only for now: the relative signal was validated with XGBoost, whose
shallow/regularised trees are what let it actually generalise; Random Forest
was shown (in the BUY/SELL models) to largely overfit sentiment/date-shared
features rather than learn from them; the same risk applies here and hasn't
been separately validated for this label. Add RF support later if wanted.
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import shutil
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from pathlib import Path

from xgboost import XGBClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
import matplotlib.pyplot as plt

from stats_utils import (
    bootstrap_auc_ci,
    permutation_importance_single_fold,
    aggregate_importance_arrays,
    correlation_redundancy_audit,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MODEL_SUFFIX = "_relative"
MODEL_NAME = "XGBoost (Relative Strength)"
LABEL_COL = "Label_10d_relative"

# Same rank-feature source columns and naming as
# src/03_feature_engineering.py::add_cross_sectional_features - kept as a
# separate list here (rather than imported) since that script isn't a
# module other scripts import from, matching this repo's existing
# convention of each 0X_*.py script being a standalone runnable step.
RANK_FEATURE_SOURCES = [
    "RSI_dist_50", "BB_width", "ATR_ratio", "Price_vs_SMA20",
    "MACD_hist", "Ret_10d", "Ret_5d", "Ret_1d", "Vol_10d", "Gap_pct",
]
EXTRA_FEATURES = [f"{col}_rank" for col in RANK_FEATURE_SOURCES] + ["Market_vol_regime"]

df = pd.read_parquet(os.path.join(PROCESSED_DIR, "all_stocks_labeled.parquet"))
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)

with open(os.path.join(PROCESSED_DIR, "fold_config.json")) as fp:
    config = json.load(fp)

# Only the fold date boundaries are shared with the BUY/SELL models - this
# model defines its own feature list and label, both below.
FOLDS = config["folds"]
FEATURE_COLS = config["feature_cols"] + EXTRA_FEATURES
LATEST_FOLD = max(int(fold["fold"]) for fold in FOLDS)

missing = [c for c in FEATURE_COLS if c not in df.columns]
if missing:
    raise ValueError(f"Missing feature columns: {missing} - did you run 03_feature_engineering.py?")
if LABEL_COL not in df.columns:
    raise ValueError(f"Missing label column {LABEL_COL} - did you run 04_label_construction.py?")

print(f"Loaded: {df.shape[0]:,} rows | {len(FEATURE_COLS)} features | label: {LABEL_COL}")
print(f"Model: {MODEL_NAME}")

pos_count = (df[LABEL_COL] == 1).sum()
neg_count = (df[LABEL_COL] == 0).sum()
spw = round(neg_count / pos_count, 2)
print(f"scale_pos_weight: {spw}  (neg/pos ratio)")

XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 10,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "scale_pos_weight": spw,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "use_label_encoder": False,
    "random_state": 42,
    "n_jobs": -1,
}


def build_model():
    return XGBClassifier(**XGB_PARAMS, verbosity=0)


all_predictions = []
fold_metrics = []
fold_importances = []

print("\n" + "=" * 65)
print("WALK-FORWARD TRAINING")
print("=" * 65)

for f in FOLDS:
    fold_num = f["fold"]

    train_df = df[df["Date"] <= f["train_end"]].copy()
    test_df = df[(df["Date"] >= f["test_start"]) & (df["Date"] <= f["test_end"])].copy()

    train_df = train_df.dropna(subset=FEATURE_COLS + [LABEL_COL])
    test_df = test_df.dropna(subset=FEATURE_COLS + [LABEL_COL])

    X_train_raw = train_df[FEATURE_COLS].values
    y_train = train_df[LABEL_COL].values
    X_test_raw = test_df[FEATURE_COLS].values
    y_test = test_df[LABEL_COL].values

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    model = build_model()
    model.fit(X_train, y_train)  # kept raw for feature/permutation importance

    # See 06_train_model.py for the full rationale: shuffled StratifiedKFold
    # (not the default, which turns into contiguous time-block folds on this
    # chronologically-sorted data) and ensemble=False (keeps pickle size sane).
    calibrator = CalibratedClassifierCV(
        build_model(), method="sigmoid",
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
        ensemble=False,
    )
    calibrator.fit(X_train, y_train)

    proba = calibrator.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)
    auc_point, auc_low, auc_high = bootstrap_auc_ci(y_test, proba, n_boot=1000)

    print(f"  Fold {fold_num}: train={len(train_df):>7,} rows | "
          f"test={len(test_df):>6,} rows | AUC={auc:.4f}  "
          f"(95% CI: {auc_low:.4f}-{auc_high:.4f})")

    test_df = test_df.copy()
    test_df["Pred_proba"] = proba
    test_df["Fold"] = fold_num
    test_df["Pred_label"] = (proba >= 0.5).astype(int)

    all_predictions.append(test_df)
    fold_metrics.append({
        "fold": fold_num,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "auc": auc,
        "auc_ci_low": auc_low,
        "auc_ci_high": auc_high,
        "test_period": f"{f['test_start']} → {f['test_end']}",
    })

    fold_importances.append(
        permutation_importance_single_fold(
            model, scaler, X_test_raw, y_test, n_repeats=5, random_state=42, scoring="roc_auc",
        )
    )

    model_dir = os.path.join(PROCESSED_DIR, "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"model_fold{fold_num}{MODEL_SUFFIX}.pkl")
    with open(model_path, "wb") as fp:
        pickle.dump({"model": model, "calibrator": calibrator, "scaler": scaler,
                     "features": FEATURE_COLS, "family": "xgboost"}, fp)
    if int(fold_num) == LATEST_FOLD:
        latest_path = os.path.join(model_dir, f"model_latest{MODEL_SUFFIX}.pkl")
        shutil.copy2(model_path, latest_path)

combined_preds = pd.concat(all_predictions, ignore_index=True)

print("\n" + "=" * 65)
print("OVERALL PERFORMANCE SUMMARY")
print("=" * 65)

overall_auc = roc_auc_score(combined_preds[LABEL_COL], combined_preds["Pred_proba"])
overall_auc_point, overall_auc_low, overall_auc_high = bootstrap_auc_ci(
    combined_preds[LABEL_COL].values, combined_preds["Pred_proba"].values, n_boot=2000
)
print(f"\nOverall out-of-sample AUC: {overall_auc:.4f}  "
      f"(95% CI: {overall_auc_low:.4f}-{overall_auc_high:.4f})")
print(f"Total out-of-sample predictions: {len(combined_preds):,}")

print(f"\n{'Fold':<6} {'Period':<35} {'AUC':>8}")
print("-" * 50)
for fm in fold_metrics:
    bar_len = int((fm["auc"] - 0.45) * 100)
    bar = "█" * max(0, bar_len)
    print(f"  {fm['fold']:<4} {fm['test_period']:<35} {fm['auc']:.4f}  {bar}")

mean_auc = np.mean([fm["auc"] for fm in fold_metrics])
std_auc = np.std([fm["auc"] for fm in fold_metrics])
below_half = sum(1 for fm in fold_metrics if fm["auc"] < 0.5)
print(f"\n  Mean AUC across folds: {mean_auc:.4f} ± {std_auc:.4f}")
print(f"  Folds with AUC < 0.5: {below_half}/{len(fold_metrics)}")
print(f"  (Std deviation measures consistency across time periods)")

print("\n" + "=" * 65)
print("CLASSIFICATION REPORT (threshold = 0.50)")
print("=" * 65)
print(classification_report(
    combined_preds[LABEL_COL],
    combined_preds["Pred_label"],
    target_names=["Label=0 (underperformed peers)", "Label=1 (beat peers)"],
))

last_model = pickle.load(
    open(os.path.join(PROCESSED_DIR, "models", f"model_fold{LATEST_FOLD}{MODEL_SUFFIX}.pkl"), "rb")
)["model"]

importances = pd.Series(last_model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=True)

plt.figure(figsize=(9, 8))
importances.plot(kind="barh", color="seagreen", edgecolor="none")
plt.axvline(1 / len(FEATURE_COLS), color="red", linestyle="--",
            label=f"Uniform baseline ({1 / len(FEATURE_COLS):.3f})")
plt.title(f"Feature importance (gain) - Fold {LATEST_FOLD} Relative Strength model\n"
          "(features above red line contribute more than average)")
plt.xlabel("Importance score")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"feature_importance{MODEL_SUFFIX}.png"), dpi=150)
plt.show()

print("\n" + "=" * 65)
print("PERMUTATION IMPORTANCE (aggregated across all folds)")
print("=" * 65)
perm_importance_df = aggregate_importance_arrays(fold_importances, FEATURE_COLS)
print(perm_importance_df.to_string(index=False))

perm_plot_df = perm_importance_df.sort_values("importance_mean", ascending=True)
plt.figure(figsize=(9, 8))
plt.barh(
    perm_plot_df["feature"], perm_plot_df["importance_mean"],
    xerr=perm_plot_df["importance_std"], color="darkorange", edgecolor="none",
)
plt.axvline(0, color="black", linewidth=0.8)
plt.title(f"Permutation importance ({MODEL_NAME}, mean ± std across "
          f"{perm_importance_df['n_folds'].iloc[0]} folds)\n"
          "Drop in out-of-sample AUC when the feature is shuffled")
plt.xlabel("Mean AUC drop")
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"permutation_importance{MODEL_SUFFIX}.png"), dpi=150)
plt.show()

print("\n" + "=" * 65)
print("FEATURE CORRELATION / REDUNDANCY AUDIT (|corr| >= 0.85)")
print("=" * 65)
redundancy_df = correlation_redundancy_audit(df.dropna(subset=FEATURE_COLS), FEATURE_COLS, threshold=0.85)
if redundancy_df.empty:
    print("No feature pairs exceed the 0.85 correlation threshold.")
else:
    print(redundancy_df.to_string(index=False))

combined_preds.to_parquet(os.path.join(PROCESSED_DIR, f"oos_predictions{MODEL_SUFFIX}.parquet"), index=False)

metrics_df = pd.DataFrame(fold_metrics)
metrics_df.to_csv(os.path.join(PROCESSED_DIR, f"fold_metrics{MODEL_SUFFIX}.csv"), index=False)
perm_importance_df.to_csv(os.path.join(PROCESSED_DIR, f"permutation_importance{MODEL_SUFFIX}.csv"), index=False)
redundancy_df.to_csv(os.path.join(PROCESSED_DIR, f"feature_redundancy{MODEL_SUFFIX}.csv"), index=False)

print(f"\nSaved out-of-sample predictions → oos_predictions{MODEL_SUFFIX}.parquet")
print(f"Saved fold metrics              → fold_metrics{MODEL_SUFFIX}.csv")
print(f"Saved permutation importance     → permutation_importance{MODEL_SUFFIX}.csv")
print(f"Saved feature redundancy audit   → feature_redundancy{MODEL_SUFFIX}.csv")
print(f"\nRelative Strength model training complete!")
