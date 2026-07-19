"""
Fast, isolated experiment harness to test candidate AUC improvements before
committing them to the real pipeline (src/03-08). Does NOT touch any
production file - reads all_stocks_labeled.parquet + fold_config.json and
writes only into experiments/results.csv.

For speed, each config trains one plain XGBoost per fold (same params as
src/06_train_model.py's XGB_PARAMS) and reports only AUC - no bootstrap CI,
no permutation importance, no calibration. Those are diagnostic/reporting
concerns; here we just need a fast relative comparison between candidate
label/feature configs to decide what's worth building into the real
pipeline.

Candidates tested (see PLAN.md discussion):
  A. baseline           - current Label_10d + current FEATURE_COLS
  B. relative_label      - label = did the stock beat the day's cross-
                           sectional mean forward return (removes market beta
                           noise from the target)
  C. rank_features        - add same-day percentile-rank versions of the top
                           permutation-importance features (normalizes out
                           market-wide moves, applies to every row)
  D. regime_feature       - add a market-wide realized-volatility regime
                           feature (20d rolling std of the cross-sectional
                           mean daily return)
  E. rank + regime         - combine C + D
  F. relative + rank + regime - combine B + C + D
"""

import json
import os
import time
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

with open(PROCESSED_DIR / "fold_config.json") as f:
    FOLD_CONFIG = json.load(f)
FOLDS = FOLD_CONFIG["folds"]
BASE_FEATURE_COLS = FOLD_CONFIG["feature_cols"]

XGB_PARAMS = {
    "n_estimators": 300,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 10,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "objective": "binary:logistic",
    "eval_metric": "auc",
    "use_label_encoder": False,
    "random_state": 42,
    "n_jobs": -1,
}

TOP_FEATURES_FOR_RANK = [
    "RSI_dist_50", "BB_width", "ATR_ratio", "Price_vs_SMA20",
    "MACD_hist", "Ret_10d", "Ret_5d", "Ret_1d", "Vol_10d", "Gap_pct",
]


def load_base_df():
    df = pd.read_parquet(PROCESSED_DIR / "all_stocks_labeled.parquet")
    df["Date"] = pd.to_datetime(df["Date"])
    return df.sort_values("Date").reset_index(drop=True)


def add_relative_label(df, threshold=0.0):
    """Label = 1 if stock's Fwd_ret_10d beats the day's cross-sectional mean
    forward return by more than `threshold`. Removes market-beta noise from
    the target - only the future Fwd_ret_10d (already used by the existing
    absolute label) is involved, so this is a relabeling, not a new feature/
    leakage."""
    mkt_fwd_ret = df.groupby("Date")["Fwd_ret_10d"].transform("mean")
    df = df.copy()
    df["Relative_fwd_ret_10d"] = df["Fwd_ret_10d"] - mkt_fwd_ret
    df["Label_10d_relative"] = np.where(
        df["Relative_fwd_ret_10d"].notna(),
        (df["Relative_fwd_ret_10d"] > threshold).astype(int),
        np.nan,
    )
    return df


def add_rank_features(df, cols=TOP_FEATURES_FOR_RANK):
    """Same-day percentile rank (0-1) of each feature across all stocks
    trading that date - normalizes out market-wide moves, unlike the raw
    value. Applies to every row (no sparsity issue, unlike symbol-level
    sentiment)."""
    df = df.copy()
    rank_cols = []
    for col in cols:
        rank_col = f"{col}_rank"
        df[rank_col] = df.groupby("Date")[col].rank(pct=True)
        rank_cols.append(rank_col)
    return df, rank_cols


def add_regime_feature(df):
    """Market-wide realized-volatility regime: 20-day rolling std of the
    cross-sectional mean daily return. Purely backward-looking (built from
    Ret_1d, already known at time T) - flags unusual macro regimes (e.g.
    2020 COVID crash, 2022 crisis) that the per-stock technical features
    can't see on their own."""
    df = df.copy()
    daily_mkt_ret = df.groupby("Date")["Ret_1d"].mean().sort_index()
    regime = daily_mkt_ret.rolling(20, min_periods=5).std()
    regime.name = "Market_vol_regime"
    df = df.merge(regime, left_on="Date", right_index=True, how="left")
    df["Market_vol_regime"] = df["Market_vol_regime"].fillna(0.0)
    return df


def run_fold_aucs(df, feature_cols, label_col):
    aucs = []
    for f in FOLDS:
        train_df = df[df["Date"] <= f["train_end"]].dropna(subset=feature_cols + [label_col])
        test_df = df[(df["Date"] >= f["test_start"]) & (df["Date"] <= f["test_end"])].dropna(subset=feature_cols + [label_col])
        if len(train_df) < 1000 or len(test_df) < 100:
            aucs.append(np.nan)
            continue

        X_train = train_df[feature_cols].values
        y_train = train_df[label_col].values
        X_test = test_df[feature_cols].values
        y_test = test_df[label_col].values

        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)

        model = XGBClassifier(**XGB_PARAMS, verbosity=0)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]
        aucs.append(roc_auc_score(y_test, proba))
    return aucs


def main():
    print("Loading base data...")
    df = load_base_df()

    print("Building candidate features/labels...")
    df = add_relative_label(df)
    df, rank_cols = add_rank_features(df)
    df = add_regime_feature(df)

    configs = {
        "A_baseline":                    (BASE_FEATURE_COLS, "Label_10d"),
        "B_relative_label":              (BASE_FEATURE_COLS, "Label_10d_relative"),
        "C_rank_features":               (BASE_FEATURE_COLS + rank_cols, "Label_10d"),
        "D_regime_feature":              (BASE_FEATURE_COLS + ["Market_vol_regime"], "Label_10d"),
        "E_rank_and_regime":             (BASE_FEATURE_COLS + rank_cols + ["Market_vol_regime"], "Label_10d"),
        "F_relative_rank_regime":        (BASE_FEATURE_COLS + rank_cols + ["Market_vol_regime"], "Label_10d_relative"),
    }

    results = []
    for name, (feature_cols, label_col) in configs.items():
        print(f"\n{'='*60}\nConfig: {name}  (label={label_col}, n_features={len(feature_cols)})\n{'='*60}")
        t0 = time.time()
        aucs = run_fold_aucs(df, feature_cols, label_col)
        elapsed = time.time() - t0
        valid_aucs = [a for a in aucs if not np.isnan(a)]
        mean_auc = np.mean(valid_aucs)
        std_auc = np.std(valid_aucs)
        below_half = sum(1 for a in valid_aucs if a < 0.5)
        print(f"  Per-fold AUC: {[round(a, 4) if not np.isnan(a) else None for a in aucs]}")
        print(f"  Mean AUC: {mean_auc:.4f} +/- {std_auc:.4f}  |  folds<0.5: {below_half}/{len(valid_aucs)}  |  {elapsed:.0f}s")
        results.append({
            "config": name, "label_col": label_col, "n_features": len(feature_cols),
            "mean_auc": mean_auc, "std_auc": std_auc, "folds_below_half": below_half,
            "fold_aucs": aucs,
        })

    results_df = pd.DataFrame(results).sort_values("mean_auc", ascending=False)
    print(f"\n{'='*60}\nRANKED RESULTS\n{'='*60}")
    print(results_df[["config", "label_col", "n_features", "mean_auc", "std_auc", "folds_below_half"]].to_string(index=False))

    out_dir = Path(__file__).resolve().parent
    results_df.to_csv(out_dir / "results.csv", index=False)
    print(f"\nSaved -> {out_dir / 'results.csv'}")


if __name__ == "__main__":
    main()
