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
LABEL_COL    = config["label_col"]
LATEST_FOLD = max(int(fold["fold"]) for fold in FOLDS)

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
print(f"scale_pos_weight: {spw}  (neg/pos ratio)")

XGB_PARAMS = {
    "n_estimators":      300,    # Number of trees. More = slower but potentially better.
                                 # 300 is a good starting point for this dataset size.

    "max_depth":         4,      # How deep each tree can grow.
                                 # Shallow trees (3-5) prevent overfitting.
                                 # Deep trees memorise noise.

    "learning_rate":     0.05,   # How much each tree contributes to the final answer.
                                 # Small values (0.01-0.1) require more trees but generalise better.
                                 # Think of it as "step size" when learning.

    "subsample":         0.8,    # Each tree only sees 80% of training rows (randomly selected).
                                 # This adds randomness and prevents overfitting.

    "colsample_bytree":  0.8,    # Each tree only sees 80% of features.
                                 # Prevents the model from over-relying on any single feature.

    "min_child_weight":  10,     # A leaf node must have at least 10 samples.
                                 # Higher values = more conservative splits = less overfitting.
                                 # Very important for financial data where patterns are subtle.

    "reg_alpha":         0.1,    # L1 regularisation: pushes less-useful feature weights to zero.
                                 # Effectively performs feature selection automatically.

    "reg_lambda":        1.0,    # L2 regularisation: keeps all weights small.
                                 # Reduces sensitivity to individual noisy samples.

    "scale_pos_weight":  spw,    # Handles class imbalance (calculated above)

    "objective":        "binary:logistic",  # We're predicting probability of label=1
    "eval_metric":      "auc",              # Optimise for AUC during training
    "use_label_encoder": False,
    "random_state":      42,
    "n_jobs":           -1,      # Use all CPU cores for speed
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



all_predictions = []   # Will hold out-of-sample predictions from all folds
fold_metrics    = []   # Will hold AUC scores per fold
fold_importances = []  # Will hold each fold's permutation-importance array

print("\n" + "="*65)
print("WALK-FORWARD TRAINING")
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
    X_train = scaler.fit_transform(X_train_raw)   # fit + transform train
    X_test  = scaler.transform(X_test_raw)        # transform test only

    model = build_model(MODEL_FAMILY, MODEL_PARAMS)
    model.fit(X_train, y_train)  # kept raw for feature/permutation importance

    # Calibration report (see 07_backtest.py) showed raw probabilities are
    # overconfident - e.g. a 0.63 "confidence" only won ~40% of the time.
    # CalibratedClassifierCV refits on 5 internal folds of the TRAINING data
    # only (no test leakage) and rescales predict_proba to match observed
    # frequencies. This is what actually gets served as "confidence".
    #
    # cv must be an explicit SHUFFLED StratifiedKFold: X_train's rows are
    # chronologically sorted, and CalibratedClassifierCV's default cv=<int>
    # uses non-shuffled StratifiedKFold, which turns into contiguous
    # TIME-BLOCK folds on sorted data. That measurably destroyed
    # discrimination in testing (AUC 0.559 -> 0.430 on fold 1) even though
    # it never touches the test fold - shuffling fixed it (AUC 0.559 -> 0.561).
    #
    # ensemble=False: fit ONE base estimator on the full training data and
    # calibrate it using cross_val_predict's out-of-fold predictions, instead
    # of the default ensemble=True which stores 5 full model clones inside
    # the calibrator. With ensemble=True each fold's pickle ballooned to
    # 350-400MB (vs ~60MB uncalibrated); ensemble=False keeps the same AUC
    # (calibration is a monotonic rescaling of one model) at ~1/5th the size.
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

    # Computed here, right after this fold's model is trained, rather than
    # stashing {model, scaler, X_test, y_test} for every fold and processing
    # them all at the end - holding N folds' full models (e.g. 9 Random
    # Forests with 400 trees each, plus their joblib worker pools) resident
    # simultaneously exhausted memory and crashed a later fold's pickle
    # write. This way only one fold's model is ever in memory at a time.
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
                     "features": FEATURE_COLS, "family": MODEL_FAMILY}, fp)
    if int(fold_num) == LATEST_FOLD:
        latest_path = os.path.join(model_dir, f"model_latest{MODEL_SUFFIX}.pkl")
        # The API predicts through the calibrated estimator. Keeping a second
        # raw Random Forest in the deployment bundle nearly doubles the pickle
        # past GitHub's 100 MB object limit, so omit that duplicate for RF.
        deployment_model = model if MODEL_FAMILY == "xgboost" else None
        with open(latest_path, "wb") as fp:
            pickle.dump({
                "model": deployment_model,
                "calibrator": calibrator,
                "scaler": scaler,
                "features": FEATURE_COLS,
                "family": MODEL_FAMILY,
            }, fp)


combined_preds = pd.concat(all_predictions, ignore_index=True)

print("\n" + "="*65)
print("OVERALL PERFORMANCE SUMMARY")
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
    target_names=["Label=0 (fail)", "Label=1 (success)"]
))

last_model = pickle.load(
    open(os.path.join(PROCESSED_DIR, "models", f"model_fold{LATEST_FOLD}{MODEL_SUFFIX}.pkl"), "rb")
)["model"]

importances = pd.Series(
    last_model.feature_importances_,
    index=FEATURE_COLS
).sort_values(ascending=True)

plt.figure(figsize=(9, 7))
importances.plot(kind="barh", color="steelblue", edgecolor="none")
plt.axvline(1/len(FEATURE_COLS), color="red", linestyle="--",
            label=f"Uniform baseline ({1/len(FEATURE_COLS):.3f})")
plt.title(f"Feature importance (gain) - Fold {LATEST_FOLD} model only\n"
          "(features above red line contribute more than average)")
plt.xlabel("Importance score")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"feature_importance{MODEL_SUFFIX}.png"), dpi=150)
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
plt.title(f"Permutation importance ({MODEL_NAME}, mean ± std across "
          f"{perm_importance_df['n_folds'].iloc[0]} folds)\n"
          "Drop in out-of-sample AUC when the feature is shuffled")
plt.xlabel("Mean AUC drop")
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, f"permutation_importance{MODEL_SUFFIX}.png"), dpi=150)
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

combined_preds.to_parquet(
    os.path.join(PROCESSED_DIR, f"oos_predictions{MODEL_SUFFIX}.parquet"), index=False
)

metrics_df = pd.DataFrame(fold_metrics)
metrics_df.to_csv(os.path.join(PROCESSED_DIR, f"fold_metrics{MODEL_SUFFIX}.csv"), index=False)
perm_importance_df.to_csv(
    os.path.join(PROCESSED_DIR, f"permutation_importance{MODEL_SUFFIX}.csv"), index=False
)
redundancy_df.to_csv(
    os.path.join(PROCESSED_DIR, f"feature_redundancy{MODEL_SUFFIX}.csv"), index=False
)

print(f"\nSaved out-of-sample predictions → oos_predictions{MODEL_SUFFIX}.parquet")
print(f"Saved fold metrics              → fold_metrics{MODEL_SUFFIX}.csv")
print(f"Saved permutation importance     → permutation_importance{MODEL_SUFFIX}.csv")
print(f"Saved feature redundancy audit   → feature_redundancy{MODEL_SUFFIX}.csv")
print(f"\nModel training complete! Next: backtesting with transaction costs.")
