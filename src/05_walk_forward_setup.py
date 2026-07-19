import json
import os
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PRIMARY_LABEL = "Label_10d"

FEATURE_COLS = [
    # Ret_20d, RSI_slope_3, and BB_pctB were dropped after permutation-importance
    # analysis showed consistently negative-or-negligible out-of-sample AUC
    # contribution in BOTH model families (they were fitting noise, not signal).
    # BB_pctB was additionally redundant with RSI_dist_50 (|corr|=0.86) which is
    # far stronger. See data/processed/permutation_importance*.csv and
    # feature_redundancy*.csv for the underlying numbers.
    "RSI_dist_50", "MACD_hist", "MACD_hist_slope_3",
    "EMA_cross", "Price_vs_SMA20",
    "BB_width", "ATR_ratio", "Vol_10d",
    "Volume_ratio", "Volume_spike", "OBV_slope_norm",
    "Ret_1d", "Ret_3d", "Ret_5d", "Ret_10d", "Ret_momentum",
    "In_uptrend", "RSI_oversold", "RSI_overbought", "HL_range_pct", "Gap_pct",
    "Sentiment_score", "Sentiment_available",
]

EMBARGO_DAYS = 20
MIN_TRAIN_YEARS = 6
TEST_START_MONTH = 2
TEST_START_DAY = 1
MIN_TRAIN_ROWS = 1_000
MIN_TEST_ROWS = 100


def build_walk_forward_folds(df: pd.DataFrame) -> list[dict]:
    """Build expanding yearly walk-forward folds from the available data."""
    data_start = df["Date"].min().normalize()
    data_end = df["Date"].max().normalize()
    first_test_year = data_start.year + MIN_TRAIN_YEARS

    folds = []
    for test_year in range(first_test_year, data_end.year + 1):
        train_end = pd.Timestamp(year=test_year - 1, month=12, day=31)
        test_start = pd.Timestamp(year=test_year, month=TEST_START_MONTH, day=TEST_START_DAY)
        test_end = min(pd.Timestamp(year=test_year, month=12, day=31), data_end)

        if test_start > data_end or test_end < test_start:
            continue

        train_df = df[df["Date"] <= train_end].dropna(subset=FEATURE_COLS + [PRIMARY_LABEL])
        test_df = df[(df["Date"] >= test_start) & (df["Date"] <= test_end)].dropna(
            subset=FEATURE_COLS + [PRIMARY_LABEL]
        )

        if len(train_df) < MIN_TRAIN_ROWS or len(test_df) < MIN_TEST_ROWS:
            print(
                f"Skipping {test_year}: train_rows={len(train_df):,}, "
                f"test_rows={len(test_df):,}"
            )
            continue

        folds.append(
            {
                "fold": len(folds) + 1,
                "train_start": str(data_start.date()),
                "train_end": str(train_end.date()),
                "test_start": str(test_start.date()),
                "test_end": str(test_end.date()),
            }
        )

    if not folds:
        raise ValueError("No valid walk-forward folds could be built from the available data.")

    return folds


df = pd.read_parquet(os.path.join(PROCESSED_DIR, "all_stocks_labeled.parquet"))
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)

missing_features = [feature for feature in FEATURE_COLS if feature not in df.columns]
if missing_features:
    raise ValueError(f"Missing feature columns: {missing_features}")
if PRIMARY_LABEL not in df.columns:
    raise ValueError(f"Missing label column: {PRIMARY_LABEL}")

print(f"Loaded: {df.shape[0]:,} rows")
print(f"Date range: {df['Date'].min().date()} -> {df['Date'].max().date()}")
print(f"Stocks: {df['Symbol'].nunique()}")
print(f"Features: {len(FEATURE_COLS)}")

folds = build_walk_forward_folds(df)

print("\n" + "=" * 70)
print("WALK-FORWARD FOLD SUMMARY")
print("=" * 70)
print(f"{'Fold':<6} {'Train period':<25} {'Test period':<22} "
      f"{'Train rows':>11} {'Test rows':>10} {'Train+':>8} {'Test+':>8}")
print("-" * 70)

fold_stats = []

for f in folds:
    train_mask = df["Date"] <= f["train_end"]
    test_mask = (df["Date"] >= f["test_start"]) & (df["Date"] <= f["test_end"])

    train_df = df[train_mask].dropna(subset=FEATURE_COLS + [PRIMARY_LABEL])
    test_df = df[test_mask].dropna(subset=FEATURE_COLS + [PRIMARY_LABEL])

    train_pos = int(train_df[PRIMARY_LABEL].sum())
    test_pos = int(test_df[PRIMARY_LABEL].sum())

    train_period = f"{f['train_start']} -> {f['train_end']}"
    test_period = f"{f['test_start']} -> {f['test_end']}"

    print(f"  {f['fold']:<4} {train_period:<25} {test_period:<22} "
          f"{len(train_df):>11,} {len(test_df):>10,} "
          f"{train_pos:>8,} {test_pos:>8,}")

    fold_stats.append({
        "fold": f["fold"],
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "train_pos": train_pos,
        "test_pos": test_pos,
        "train_pct": train_pos / len(train_df) * 100 if len(train_df) > 0 else 0,
        "test_pct": test_pos / len(test_df) * 100 if len(test_df) > 0 else 0,
    })

print("\n(Train+ and Test+ = number of Label=1 rows in each split)")

print("\n" + "=" * 50)
print("LEAKAGE CHECK")
print("=" * 50)

for f in folds:
    train_dates = df[df["Date"] <= f["train_end"]]["Date"]
    test_dates = df[(df["Date"] >= f["test_start"]) & (df["Date"] <= f["test_end"])]["Date"]

    overlap = (train_dates.max() >= test_dates.min()) if len(test_dates) > 0 else False
    status = "OVERLAP DETECTED" if overlap else "Clean"
    print(f"  Fold {f['fold']}: {status}")

fig, ax = plt.subplots(figsize=(14, 5))

colors_train = "#2196F3"
colors_test = "#FF9800"
timeline_start = df["Date"].min().normalize()

for i, f in enumerate(folds):
    y = i * 1.2

    train_start_dt = pd.Timestamp(f["train_start"])
    train_end_dt = pd.Timestamp(f["train_end"])
    test_start_dt = pd.Timestamp(f["test_start"])
    test_end_dt = pd.Timestamp(f["test_end"])

    ax.barh(
        y,
        (train_end_dt - train_start_dt).days,
        left=(train_start_dt - timeline_start).days,
        height=0.8,
        color=colors_train,
        alpha=0.7,
    )

    ax.barh(
        y,
        (test_end_dt - test_start_dt).days,
        left=(test_start_dt - timeline_start).days,
        height=0.8,
        color=colors_test,
        alpha=0.9,
    )

    ax.text(-30, y, f"Fold {f['fold']}", va="center", ha="right", fontsize=9)

ax.set_xlabel(f"Days from {timeline_start.date()}")
ax.set_title("Walk-forward validation folds\n(blue = train, orange = test)")
ax.set_yticks([])

train_patch = mpatches.Patch(color=colors_train, alpha=0.7, label="Training period")
test_patch = mpatches.Patch(color=colors_test, alpha=0.9, label="Test period")
ax.legend(handles=[train_patch, test_patch])

plt.tight_layout()
plt.savefig(os.path.join(PROCESSED_DIR, "walk_forward_folds.png"), dpi=150)
if plt.get_backend().lower() != "agg":
    plt.show()
print("\nFold visualisation saved")

fold_config = {
    "folds": folds,
    "feature_cols": FEATURE_COLS,
    "label_col": PRIMARY_LABEL,
    "embargo_days": EMBARGO_DAYS,
    "min_train_years": MIN_TRAIN_YEARS,
    "test_start_month": TEST_START_MONTH,
    "test_start_day": TEST_START_DAY,
    "min_train_rows": MIN_TRAIN_ROWS,
    "min_test_rows": MIN_TEST_ROWS,
}

config_path = os.path.join(PROCESSED_DIR, "fold_config.json")
with open(config_path, "w", encoding="utf-8") as fp:
    json.dump(fold_config, fp, indent=2)

print(f"Fold config saved -> {config_path}")
print("\nWalk-forward setup complete! Next: model training.")
