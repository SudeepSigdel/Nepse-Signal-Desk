"""
Build backtest MarketData from pipeline artifacts.

Prices and liquidity come from the full feature history (so the trailing
liquidity filter is warm from day one). Probabilities come ONLY from the
walk-forward out-of-sample predictions: each one was made by a model that
never saw that year, which is what makes an agent backtest honest.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from app.trading.backtest import MarketData, add_liquidity

PRICE_COLUMNS = ["Symbol", "Date", "Open", "High", "Low", "Close", "Volume", "Turnover"]
# NEPSE's daily circuit is ±10%, so a bigger close-to-close gap can't be a real
# trade - it's a bonus/right share adjustment (or a bad row) in unadjusted data.
CORPORATE_ACTION_GAP = 0.105


def adjust_for_corporate_actions(frame: pd.DataFrame, gap: float = CORPORATE_ACTION_GAP) -> tuple[pd.DataFrame, int]:
    """
    Back-adjust prices so impossible overnight gaps don't read as crashes or
    windfalls. Each gap's ratio rescales all earlier prices of that symbol
    (volumes inversely), the standard construction of an adjusted series.
    Returns (adjusted frame, number of gaps adjusted).
    """
    df = frame.sort_values(["Symbol", "Date"]).copy()
    ratio = df["Close"] / df.groupby("Symbol")["Close"].shift(1)
    is_gap = (ratio - 1).abs() > gap
    step = ratio.where(is_gap, 1.0).fillna(1.0)
    # factor for row i = product of gap ratios strictly after i (within the symbol)
    later = step.groupby(df["Symbol"]).transform(lambda s: s[::-1].cumprod()[::-1].shift(-1, fill_value=1.0))
    for column in ("Open", "High", "Low", "Close"):
        if column in df:
            df[column] = df[column] * later
    if "Volume" in df:
        df["Volume"] = df["Volume"] / later
    return df, int(is_gap.sum())


def family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


def load_market_frame(processed_dir: Path, family: str = "xgboost") -> pd.DataFrame:
    prices = pd.read_parquet(processed_dir / "all_stocks_features.parquet", columns=PRICE_COLUMNS)
    prices["Date"] = pd.to_datetime(prices["Date"])
    prices, gaps = adjust_for_corporate_actions(prices)
    prices.attrs["corporate_action_gaps"] = gaps
    prices = add_liquidity(prices)

    suffix = family_suffix(family)
    buy = pd.read_parquet(processed_dir / f"oos_predictions{suffix}.parquet", columns=["Symbol", "Date", "Pred_proba", "Fold"])
    buy = buy.rename(columns={"Pred_proba": "buy_proba", "Fold": "fold"})
    frame = prices.merge(buy, on=["Symbol", "Date"], how="left")

    sell_path = processed_dir / f"oos_predictions{suffix}_sell.parquet"
    if sell_path.exists():
        sell = pd.read_parquet(sell_path, columns=["Symbol", "Date", "Pred_proba"]).rename(
            columns={"Pred_proba": "sell_proba"}
        )
        frame = frame.merge(sell, on=["Symbol", "Date"], how="left")
    return frame


def load_market_data(
    processed_dir: Path, family: str = "xgboost", start: Optional[str] = None, end: Optional[str] = None
) -> MarketData:
    """MarketData limited to [start, end]; defaults to the out-of-sample prediction period."""
    frame = load_market_frame(processed_dir, family)
    has_pred = frame["buy_proba"].notna()
    lo = pd.Timestamp(start) if start else frame.loc[has_pred, "Date"].min()
    hi = pd.Timestamp(end) if end else frame.loc[has_pred, "Date"].max()
    return MarketData(frame[(frame["Date"] >= lo) & (frame["Date"] <= hi)])
