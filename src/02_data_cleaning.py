import json
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scrapper"))

from app.trading.price_quality import clean_prices  # noqa: E402
from nepse_scraper import compute_indicators  # noqa: E402

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MIN_ROWS_PER_SYMBOL = 120
LOW_COVERAGE_MEDIAN_FRACTION = 0.5

df = pd.read_parquet(os.path.join(PROCESSED_DIR, "all_stocks_combined.parquet"))
print(f"Loaded: {df.shape[0]:,} rows x {df.shape[1]} columns")

# ── Price-history repair (see app/trading/price_quality.py) ──
# Removes day/month-swapped duplicates and off-calendar rows from the old
# Sharesansar date-parsing bug, drops single-day bad prints, and back-adjusts
# bonus/right-share gaps so returns, indicators and labels aren't polluted by
# fake crashes. Indicators are then recomputed on the cleaned prices.
# PRICE_REPAIR=0 skips this step (ablation / before-after comparisons only).
if os.getenv("PRICE_REPAIR", "1") != "0":
    df, quality = clean_prices(df)
    df["Percent Change"] = np.nan  # recomputed from cleaned closes by compute_indicators
    # Explicit loop: groupby.apply drops the grouping column on newer pandas.
    df = pd.concat([compute_indicators(g) for _, g in df.groupby("Symbol", sort=False)], ignore_index=True)
    print("Price repair:", ", ".join(f"{k}={v:,}" for k, v in quality.items()))
    report_dir = PROCESSED_DIR / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "data_quality.json").write_text(json.dumps(quality, indent=1))
else:
    print("Price repair skipped (PRICE_REPAIR=0)")

df["Volume"] = df.groupby("Symbol")["Volume"].ffill()

df["Daily_Return"] = df["Daily_Return"].fillna(0)
df["Log_Return"] = df["Log_Return"].fillna(0)

print("Fixed missing Volume, Daily_Return, Log_Return")

symbol_summary = (
    df.groupby("Symbol")
    .agg(Rows=("Date", "size"), Start=("Date", "min"), End=("Date", "max"))
    .sort_values(["Rows", "Symbol"])
)

short_symbols = symbol_summary[symbol_summary["Rows"] < MIN_ROWS_PER_SYMBOL]
if not short_symbols.empty:
    before = len(df)
    df = df[~df["Symbol"].isin(short_symbols.index)].copy()
    print(
        f"Removed {len(short_symbols)} symbols with fewer than {MIN_ROWS_PER_SYMBOL} rows: "
        f"{', '.join(short_symbols.index)}"
    )
    print(f"Dropped {before - len(df):,} rows from too-short symbols")
else:
    print(f"No symbols below minimum row threshold ({MIN_ROWS_PER_SYMBOL})")

remaining_summary = (
    df.groupby("Symbol")
    .agg(Rows=("Date", "size"), Start=("Date", "min"), End=("Date", "max"))
    .sort_values(["Rows", "Symbol"])
)
median_rows = remaining_summary["Rows"].median()
low_coverage = remaining_summary[remaining_summary["Rows"] < median_rows * LOW_COVERAGE_MEDIAN_FRACTION]
if not low_coverage.empty:
    print(
        f"\nSymbols with less than {LOW_COVERAGE_MEDIAN_FRACTION:.0%} of median row count "
        f"({median_rows:.0f}) are kept but flagged:"
    )
    print(low_coverage.to_string())

print(f"Remaining stocks: {df['Symbol'].nunique()}")


print("\n" + "=" * 50)
print("CHECKING FOR MID-SERIES NANS (should all be 0)")
print("="*50)

problem_cols = ["Close", "Open", "High", "Low", "Volume",
                "RSI_14", "MACD", "BB_Upper"]

for symbol, group in df.groupby("Symbol"):
    group_sorted = group.sort_values("Date")
    for col in problem_cols:
        series = group_sorted[col].values
        first_valid = pd.Series(series).first_valid_index()
        if first_valid is None:
            continue
        mid_nans = pd.Series(series[first_valid:]).isnull().sum()
        if mid_nans > 0:
            print(f"  {symbol} | {col}: {mid_nans} NaN(s) after first valid row")

print("Check complete")

output_path = os.path.join(PROCESSED_DIR, "all_stocks_clean.parquet")
df.to_parquet(output_path, index=False)

print(f"\nSaved clean data → {output_path}")
print(f"   Final shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

print("\n" + "="*50)
print("REMAINING MISSING VALUES (should only be warm-up NaNs)")
print("="*50)
missing = df.isnull().sum()
print(missing[missing > 0])
print("\nData is ready for feature engineering!")
