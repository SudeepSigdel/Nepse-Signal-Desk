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
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, classification_report
import matplotlib.pyplot as plt


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

# Verify SELL labels exist
if LABEL_COL not in df.columns:
    raise ValueError(f"{LABEL_COL} not found! Did you run 04_label_construction.py with SELL labels?")

print(f"Loaded: {df.shape[0]:,} rows | {len(FEATURE_COLS)} features | label: {LABEL_COL}")


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


all_predictions = []
fold_metrics    = []

print("\n" + "="*65)
print("TRAINING SELL CLASSIFIERS (7 folds)")
print("="*65)

for f in FOLDS:
    fold_num = f["fold"]

    train_df = df[df["Date"] <= f["train_end"]].copy()
    test_df  = df[(df["Date"] >= f["test_start"]) &
                  (df["Date"] <= f["test_end"])].copy()

    train_df = train_df.dropna(subset=FEATURE_COLS + [LABEL_COL])
    test_df  = test_df.dropna(subset=FEATURE_COLS + [LABEL_COL])

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df[LABEL_COL].values
    X_test  = test_df[FEATURE_COLS].values
    y_test  = test_df[LABEL_COL].values

    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    model = XGBClassifier(**XGB_PARAMS, verbosity=0)
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)

    print(f"  Fold {fold_num}: train={len(train_df):>7,} rows | "
          f"test={len(test_df):>6,} rows | AUC={auc:.4f}")

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
        "test_period": f"{f['test_start']} → {f['test_end']}"
    })

    # Save SELL model
    model_dir = os.path.join(PROCESSED_DIR, "models")
    os.makedirs(model_dir, exist_ok=True)
    
    # Save with _sell suffix to distinguish from BUY models
    with open(os.path.join(model_dir, f"model_fold{fold_num}_sell.pkl"), "wb") as fp:
        pickle.dump({"model": model, "scaler": scaler,
                     "features": FEATURE_COLS}, fp)
    print(f"         → Saved: model_fold{fold_num}_sell.pkl")


combined_preds = pd.concat(all_predictions, ignore_index=True)

print("\n" + "="*65)
print("SELL CLASSIFIER: OVERALL PERFORMANCE SUMMARY")
print("="*65)

overall_auc = roc_auc_score(
    combined_preds[LABEL_COL],
    combined_preds["Pred_proba"]
)
print(f"\nOverall out-of-sample AUC: {overall_auc:.4f}")
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
    open(os.path.join(PROCESSED_DIR, "models", f"model_fold7_sell.pkl"), "rb")
)["model"]

importances = pd.Series(
    last_model.feature_importances_,
    index=FEATURE_COLS
).sort_values(ascending=True)

plt.figure(figsize=(9, 7))
importances.plot(kind="barh", color="coral", edgecolor="none")
plt.axvline(1/len(FEATURE_COLS), color="red", linestyle="--",
            label=f"Uniform baseline ({1/len(FEATURE_COLS):.3f})")
plt.title("Feature importance — SELL Classifier (Fold 7)\n"
          "(features above red line contribute more than average)")
plt.xlabel("Importance score")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, "feature_importance_sell.png"), dpi=150)
plt.show()

# Save results
combined_preds.to_parquet(
    os.path.join(PROCESSED_DIR, "oos_predictions_sell.parquet"), index=False
)

metrics_df = pd.DataFrame(fold_metrics)
metrics_df.to_csv(os.path.join(PROCESSED_DIR, "fold_metrics_sell.csv"), index=False)

print(f"\nSaved out-of-sample predictions → oos_predictions_sell.parquet")
print(f"Saved fold metrics              → fold_metrics_sell.csv")
print(f"\n✓ SELL Classifier training complete!")
print(f"  All 7 models saved: model_fold*_sell.pkl")
