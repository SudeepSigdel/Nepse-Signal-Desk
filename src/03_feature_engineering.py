import pandas as pd
import numpy as np
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

df = pd.read_parquet(os.path.join(PROCESSED_DIR, "all_stocks_clean.parquet"))
print(f"Loaded: {df.shape[0]:,} rows × {df.shape[1]} columns")

from utils import per_stock

def add_momentum_features(g):
    g["RSI_dist_50"]   = g["RSI_14"] - 50
    g["RSI_slope_3"]   = g["RSI_14"].diff(3)
    g["MACD_hist"]     = g["MACD"] - g["MACD_Signal"]
    g["MACD_hist_slope_3"] = g["MACD_hist"].diff(3)
    g["EMA_cross"]     = g["EMA_12"] - g["EMA_26"]
    g["Price_vs_SMA20"] = (g["Close"] - g["SMA_20"]) / g["SMA_20"] * 100
    return g

df = per_stock(add_momentum_features, df)
print("Momentum features added")

def add_volatility_features(g):
    band_range = g["BB_Upper"] - g["BB_Lower"]
    g["BB_pctB"] = (g["Close"] - g["BB_Lower"]) / band_range
    g["BB_width"] = band_range / g["BB_Middle"] * 100
    g["ATR_ratio"] = g["ATR_14"] / g["Close"] * 100
    g["Vol_10d"] = g["Log_Return"].rolling(10).std()
    return g

df = per_stock(add_volatility_features, df)
print("Volatility features added")

def add_volume_features(g):
    vol_mean_20 = g["Volume"].rolling(20).mean()
    g["Volume_ratio"] = g["Volume"] / vol_mean_20
    g["Volume_spike"] = (g["Volume_ratio"] > 2.0).astype(int)
    g["OBV_slope_5"] = g["OBV"].diff(5)
    obv_std = g["OBV"].rolling(20).std()
    g["OBV_slope_norm"] = g["OBV_slope_5"] / (obv_std + 1e-9)
    return g

df = per_stock(add_volume_features, df)
print("Volume features added")

def add_return_features(g):
    g["Ret_1d"]  = g["Log_Return"]
    g["Ret_3d"]  = g["Log_Return"].rolling(3).sum()
    g["Ret_5d"]  = g["Log_Return"].rolling(5).sum()
    g["Ret_10d"] = g["Log_Return"].rolling(10).sum()
    g["Ret_20d"] = g["Log_Return"].rolling(20).sum()
    g["Ret_momentum"] = (g["Ret_3d"] - g["Ret_10d"]) / 2
    return g

df = per_stock(add_return_features, df)
print("Return features added")

def add_context_features(g):
    g["In_uptrend"] = (g["EMA_12"] > g["EMA_26"]).astype(int)
    g["RSI_oversold"]  = (g["RSI_14"] < 30).astype(int)
    g["RSI_overbought"] = (g["RSI_14"] > 70).astype(int)
    g["HL_range_pct"] = (g["High"] - g["Low"]) / g["Close"] * 100
    g["Gap_pct"] = (g["Open"] - g["Close"].shift(1)) / g["Close"].shift(1) * 100

    return g

df = per_stock(add_context_features, df)
print("Context features added")


def add_sentiment_features(df):
    """Join daily market-wide news sentiment (from sentiment_scoring.py).

    Sentiment coverage only exists from whenever news_scraper.py started
    running onward (see its module docstring - no historical backfill is
    available from the source site). Rows before that date, or when the
    sentiment file doesn't exist yet, get neutral 0 plus an availability
    flag so the model can tell "no news data" apart from "genuinely neutral".
    """
    sentiment_path = PROCESSED_DIR / "market_sentiment.parquet"
    if not sentiment_path.exists():
        print("  market_sentiment.parquet not found - sentiment features "
              "set to neutral/unavailable for all rows. Run "
              "scrapper/news_scraper.py + src/sentiment_scoring.py to populate.")
        df["Sentiment_score"] = 0.0
        df["Sentiment_available"] = 0
        return df

    sentiment = pd.read_parquet(sentiment_path)[["Date", "Sentiment_score_smoothed"]]
    sentiment = sentiment.rename(columns={"Sentiment_score_smoothed": "Sentiment_score"})
    sentiment["Date"] = pd.to_datetime(sentiment["Date"])

    df = df.merge(sentiment, on="Date", how="left")
    df["Sentiment_available"] = df["Sentiment_score"].notna().astype(int)
    df["Sentiment_score"] = df["Sentiment_score"].fillna(0.0)
    return df

df = add_sentiment_features(df)
print("Sentiment features added")


# Features for the Relative Strength model (src/06c_train_relative_model.py)
# only - not used by the existing BUY/SELL models, so adding them here can't
# change those models' behavior. See experiments/auc_experiments.py for the
# comparison that motivated these: on their own they barely help the
# absolute-return label (0.520 -> 0.521 AUC), but paired with a relative-
# return label they fixed every anti-predictive fold (5/9 -> 0/9 folds with
# AUC < 0.5) and lifted mean AUC from 0.520 to 0.550.
RANK_FEATURE_SOURCES = [
    "RSI_dist_50", "BB_width", "ATR_ratio", "Price_vs_SMA20",
    "MACD_hist", "Ret_10d", "Ret_5d", "Ret_1d", "Vol_10d", "Gap_pct",
]


def add_cross_sectional_features(df):
    """Same-day percentile rank (0-1) of each source feature across all
    stocks trading that date - normalizes out market-wide moves that the
    raw value conflates with genuine cross-sectional signal.

    Also adds a market-wide realized-volatility regime feature (20-day
    rolling std of the cross-sectional mean daily return) so the model can
    tell "unusual macro regime" (e.g. 2020 COVID crash, 2022 crisis) apart
    from normal trading conditions - purely backward-looking, built from
    Ret_1d which is already known at time T.
    """
    df = df.copy()
    rank_cols = []
    for col in RANK_FEATURE_SOURCES:
        rank_col = f"{col}_rank"
        df[rank_col] = df.groupby("Date")[col].rank(pct=True)
        rank_cols.append(rank_col)

    daily_mkt_ret = df.groupby("Date")["Ret_1d"].mean().sort_index()
    regime = daily_mkt_ret.rolling(20, min_periods=5).std()
    regime.name = "Market_vol_regime"
    df = df.merge(regime, left_on="Date", right_index=True, how="left")
    df["Market_vol_regime"] = df["Market_vol_regime"].fillna(0.0)

    return df, rank_cols + ["Market_vol_regime"]


df, RELATIVE_MODEL_EXTRA_FEATURES = add_cross_sectional_features(df)
print("Cross-sectional rank + regime features added (for Relative Strength model)")

new_features = [
    "RSI_dist_50", "RSI_slope_3", "MACD_hist", "MACD_hist_slope_3",
    "EMA_cross", "Price_vs_SMA20",
    "BB_pctB", "BB_width", "ATR_ratio", "Vol_10d",
    "Volume_ratio", "Volume_spike", "OBV_slope_5", "OBV_slope_norm",
    "Ret_1d", "Ret_3d", "Ret_5d", "Ret_10d", "Ret_20d", "Ret_momentum",
    "In_uptrend", "RSI_oversold", "RSI_overbought", "HL_range_pct", "Gap_pct",
    "Sentiment_score", "Sentiment_available",
]

print(f"\nNew features created: {len(new_features)}")
print(f"   Total columns now: {df.shape[1]}")
print(f"   Total rows: {df.shape[0]:,}")

print("\n" + "="*60)
print("FEATURE QUALITY CHECK")
print("="*60)
print(f"{'Feature':<22} {'NaN%':>6}  {'Min':>10}  {'Mean':>10}  {'Max':>10}")
print("-"*60)

for feat in new_features:
    nan_pct = df[feat].isna().mean() * 100
    if df[feat].dtype in [float, int] or np.issubdtype(df[feat].dtype, np.number):
        fmin  = df[feat].min()
        fmean = df[feat].mean()
        fmax  = df[feat].max()
        print(f"{feat:<22} {nan_pct:>5.1f}%  {fmin:>10.3f}  {fmean:>10.3f}  {fmax:>10.3f}")

output_path = os.path.join(PROCESSED_DIR, "all_stocks_features.parquet")
df.to_parquet(output_path, index=False)
print(f"\nSaved → {output_path}")
print("Feature engineering complete! Next: label construction.")