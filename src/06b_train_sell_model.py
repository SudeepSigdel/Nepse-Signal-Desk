"""
06b_train_sell_model.py

Train dedicated SELL classifier models (mirror of BUY models).
Each fold trains on Label_10d_sell instead of Label_10d.

SELL Label Logic:
  Label_10d_sell = 1 if (Fwd_ret_10d < -1%)  [stock drops 1%+ over next 10 days]
  Label_10d_sell = 0 otherwise

This is symmetric to the BUY label logic and answers: "Will this stock drop?"
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from pathlib import Path

from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
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

df = pd.read_parquet(os.path.join(PROCESSED_DIR, "all_stocks_labeled.parquet"))
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)

with open(os.path.join(PROCESSED_DIR, "fold_config.json")) as fp:
    config = json.load(fp)

FOLDS        = config["folds"]
FEATURE_COLS = config["feature_cols"]
LABEL_COL    = "Label_10d_sell"  # Use SELL label instead of BUY
LATEST_FOLD = max(int(fold["fold"]) for fold in FOLDS)

# Verify SELL labels exist
if LABEL_COL not in df.columns:
    raise ValueError(f"{LABEL_COL} not found! Did you run 04_label_construction.py with SELL labels?")

print(f"Loaded: {df.shape[0]:,} rows | {len(FEATURE_COLS)} features | label: {LABEL_COL}")


def normalize_model_family(raw_family: str | None) -> str:
    family = (raw_family or "xgboost").strip().lower().replace("-", "_")
    if family in {"rf", "randomforest", "random_forest", "random forest"}:
        return "random_forest"
    return "xgboost"


def family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


def build_model(family: str, params: dict):
    if family == "random_forest":
        return RandomForestClassifier(**params)
    return XGBClassifier(**params, verbosity=0)


MODEL_FAMILY = normalize_model_family(os.getenv("MODEL_FAMILY"))
MODEL_SUFFIX = family_suffix(MODEL_FAMILY)
MODEL_NAME = "Random Forest" if MODEL_FAMILY == "random_forest" else "XGBoost"

print(f"Model family: {MODEL_NAME}")


pos_count = (df[LABEL_COL] == 1).sum()
neg_count = (df[LABEL_COL] == 0).sum()
spw = round(neg_count / pos_count, 2)
print(f"scale_pos_weight: {spw}  (neg/pos ratio for SELL classifier)")

XGB_PARAMS = {
    "n_estimators":      300,
    "max_depth":         4,
    "learning_rate":     0.05,
    "subsample":         0.8,
    "colsample_bytree":  0.8,
    "min_child_weight":  10,
    "reg_alpha":         0.1,
    "reg_lambda":        1.0,
    "scale_pos_weight":  spw,
    "objective":        "binary:logistic",
    "eval_metric":      "auc",
    "use_label_encoder": False,
    "random_state":      42,
    "n_jobs":           -1,
}

RF_PARAMS = {
    "n_estimators": 400,
    "max_depth": 12,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "max_features": "sqrt",
    "class_weight": "balanced_subsample",
    "random_state": 42,
    "n_jobs": -1,
}

MODEL_PARAMS = XGB_PARAMS if MODEL_FAMILY == "xgboost" else RF_PARAMS


all_predictions = []
fold_metrics    = []
fold_importances = []  # Will hold each fold's permutation-importance array

print("\n" + "="*65)
print(f"TRAINING SELL CLASSIFIERS ({len(FOLDS)} folds)")
print("="*65)

for f in FOLDS:
    fold_num = f["fold"]

    train_df = df[df["Date"] <= f["train_end"]].copy()
    test_df  = df[(df["Date"] >= f["test_start"]) &
                  (df["Date"] <= f["test_end"])].copy()

    train_df = train_df.dropna(subset=FEATURE_COLS + [LABEL_COL])
    test_df  = test_df.dropna(subset=FEATURE_COLS + [LABEL_COL])

    X_train_raw = train_df[FEATURE_COLS].values
    y_train     = train_df[LABEL_COL].values
    X_test_raw  = test_df[FEATURE_COLS].values
    y_test      = test_df[LABEL_COL].values

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test  = scaler.transform(X_test_raw)

    model = build_model(MODEL_FAMILY, MODEL_PARAMS)
    model.fit(X_train, y_train)  # kept raw for feature importance

    # See 06_train_model.py: raw probabilities are overconfident, so the
    # SELL confidence served to users is calibrated the same way. cv must be
    # a SHUFFLED StratifiedKFold - X_train is chronologically sorted, and an
    # un-shuffled split turns into contiguous time-block folds, which
    # measurably destroyed discrimination in testing. ensemble=False keeps
    # the pickle size sane (~60MB vs 350MB+ with the default ensemble=True).
    calibrator = CalibratedClassifierCV(
        build_model(MODEL_FAMILY, MODEL_PARAMS), method="sigmoid",
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
    test_df["Pred_proba"]    = proba
    test_df["Fold"]          = fold_num
    test_df["Pred_label"]    = (proba >= 0.5).astype(int)

    all_predictions.append(test_df)
    fold_metrics.append({
        "fold":       fold_num,
        "train_rows": len(train_df),
        "test_rows":  len(test_df),
        "auc":        auc,
        "auc_ci_low": auc_low,
        "auc_ci_high": auc_high,
        "test_period": f"{f['test_start']} → {f['test_end']}"
    })

    # Computed here, right after this fold's model is trained (see
    # 06_train_model.py) rather than holding every fold's model in memory
    # until the end - that pattern crashed a later fold's pickle write on a
    # 16GB machine once Random Forest had ~7 folds' worth of 400-tree models
    # resident simultaneously.
    fold_importances.append(
        permutation_importance_single_fold(
            model, scaler, X_test_raw, y_test, n_repeats=5, random_state=42, scoring="roc_auc",
        )
    )

    # Save SELL model
    model_dir = os.path.join(PROCESSED_DIR, "models")
    os.makedirs(model_dir, exist_ok=True)
    
    # Save with _sell suffix to distinguish from BUY models
    model_path = os.path.join(model_dir, f"model_fold{fold_num}{MODEL_SUFFIX}_sell.pkl")
    with open(model_path, "wb") as fp:
        pickle.dump({"model": model, "calibrator": calibrator, "scaler": scaler,
                     "features": FEATURE_COLS, "family": MODEL_FAMILY}, fp)
    if int(fold_num) == LATEST_FOLD:
        latest_path = os.path.join(model_dir, f"model_latest{MODEL_SUFFIX}_sell.pkl")
        # The calibrated estimator is the production predictor. Avoid storing
        # a duplicate raw Random Forest in the deployable latest bundle.
        deployment_model = model if MODEL_FAMILY == "xgboost" else None
        with open(latest_path, "wb") as fp:
            pickle.dump({
                "model": deployment_model,
                "calibrator": calibrator,
                "scaler": scaler,
                "features": FEATURE_COLS,
                "family": MODEL_FAMILY,
            }, fp)
    print(f"         → Saved: model_fold{fold_num}{MODEL_SUFFIX}_sell.pkl")


combined_preds = pd.concat(all_predictions, ignore_index=True)

print("\n" + "="*65)
print("SELL CLASSIFIER: OVERALL PERFORMANCE SUMMARY")
print("="*65)

overall_auc = roc_auc_score(
    combined_preds[LABEL_COL],
    combined_preds["Pred_proba"]
)
overall_auc_point, overall_auc_low, overall_auc_high = bootstrap_auc_ci(
    combined_preds[LABEL_COL].values, combined_preds["Pred_proba"].values, n_boot=2000
)
print(f"\nOverall out-of-sample AUC: {overall_auc:.4f}  "
      f"(95% CI: {overall_auc_low:.4f}-{overall_auc_high:.4f})")
print(f"Total out-of-sample predictions: {len(combined_preds):,}")

print(f"\n{'Fold':<6} {'Period':<35} {'AUC':>8}")
print("-"*50)
for fm in fold_metrics:
    bar_len = int((fm["auc"] - 0.45) * 100)
    bar = "█" * max(0, bar_len)
    print(f"  {fm['fold']:<4} {fm['test_period']:<35} {fm['auc']:.4f}  {bar}")

mean_auc = np.mean([fm["auc"] for fm in fold_metrics])
std_auc  = np.std([fm["auc"] for fm in fold_metrics])
print(f"\n  Mean AUC across folds: {mean_auc:.4f} ± {std_auc:.4f}")
print(f"  (Std deviation measures consistency across time periods)")


print("\n" + "="*65)
print("CLASSIFICATION REPORT (threshold = 0.50)")
print("="*65)
print(classification_report(
    combined_preds[LABEL_COL],
    combined_preds["Pred_label"],
    target_names=["Label=0 (no downside)", "Label=1 (downside -1%+)"]
))

# Feature importance visualization (using last fold)
last_model = pickle.load(
    open(os.path.join(PROCESSED_DIR, "models", f"model_fold{LATEST_FOLD}{MODEL_SUFFIX}_sell.pkl"), "rb")
)["model"]

importances = pd.Series(
    last_model.feature_importances_,
    index=FEATURE_COLS
).sort_values(ascending=True)

plt.figure(figsize=(9, 7))
importances.plot(kind="barh", color="coral", edgecolor="none")
plt.axvline(1/len(FEATURE_COLS), color="red", linestyle="--",
            label=f"Uniform baseline ({1/len(FEATURE_COLS):.3f})")
plt.title(f"Feature importance - SELL Classifier (Fold {LATEST_FOLD})\n"
          "(features above red line contribute more than average)")
plt.xlabel("Importance score")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"feature_importance{MODEL_SUFFIX}_sell.png"), dpi=150)
plt.show()

print("\n" + "="*65)
print("PERMUTATION IMPORTANCE (aggregated across all folds)")
print("="*65)
print("Gain-based importance above is biased toward correlated features and\n"
      "reflects only the latest fold's model. This measures how much each\n"
      "fold's OUT-OF-SAMPLE AUC drops when a feature is shuffled, averaged\n"
      "across every fold — a feature only ranks highly if it consistently\n"
      "helps on unseen data.")

perm_importance_df = aggregate_importance_arrays(fold_importances, FEATURE_COLS)
print(perm_importance_df.to_string(index=False))

perm_plot_df = perm_importance_df.sort_values("importance_mean", ascending=True)
plt.figure(figsize=(9, 7))
plt.barh(
    perm_plot_df["feature"], perm_plot_df["importance_mean"],
    xerr=perm_plot_df["importance_std"], color="darkorange", edgecolor="none",
)
plt.axvline(0, color="black", linewidth=0.8)
plt.title(f"Permutation importance - SELL Classifier ({MODEL_NAME}, mean ± std across "
          f"{perm_importance_df['n_folds'].iloc[0]} folds)\n"
          "Drop in out-of-sample AUC when the feature is shuffled")
plt.xlabel("Mean AUC drop")
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"permutation_importance{MODEL_SUFFIX}_sell.png"), dpi=150)
plt.show()

print("\n" + "="*65)
print("FEATURE CORRELATION / REDUNDANCY AUDIT (|corr| >= 0.85)")
print("="*65)
redundancy_df = correlation_redundancy_audit(
    df.dropna(subset=FEATURE_COLS), FEATURE_COLS, threshold=0.85
)
if redundancy_df.empty:
    print("No feature pairs exceed the 0.85 correlation threshold.")
else:
    print(redundancy_df.to_string(index=False))
    print("\nHighly correlated pairs split importance credit between them and\n"
          "can make gain-based rankings misleading. Consider dropping one\n"
          "side of each pair if permutation importance agrees it's redundant.")

# Save results
combined_preds.to_parquet(
    os.path.join(PROCESSED_DIR, f"oos_predictions{MODEL_SUFFIX}_sell.parquet"), index=False
)

metrics_df = pd.DataFrame(fold_metrics)
metrics_df.to_csv(os.path.join(PROCESSED_DIR, f"fold_metrics{MODEL_SUFFIX}_sell.csv"), index=False)
perm_importance_df.to_csv(
    os.path.join(PROCESSED_DIR, f"permutation_importance{MODEL_SUFFIX}_sell.csv"), index=False
)
redundancy_df.to_csv(
    os.path.join(PROCESSED_DIR, f"feature_redundancy{MODEL_SUFFIX}_sell.csv"), index=False
)

print(f"\nSaved out-of-sample predictions → oos_predictions{MODEL_SUFFIX}_sell.parquet")
print(f"Saved fold metrics              → fold_metrics{MODEL_SUFFIX}_sell.csv")
print(f"Saved permutation importance     → permutation_importance{MODEL_SUFFIX}_sell.csv")
print(f"Saved feature redundancy audit   → feature_redundancy{MODEL_SUFFIX}_sell.csv")
print(f"\n✓ SELL Classifier training complete!")
print(f"  All {len(FOLDS)} models saved: model_fold*{MODEL_SUFFIX}_sell.pkl")
