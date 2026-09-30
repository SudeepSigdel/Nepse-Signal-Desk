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
from app.trading.price_quality import adjust_for_corporate_actions, clean_prices  # noqa: F401 (re-export)

PRICE_COLUMNS = ["Symbol", "Date", "Open", "High", "Low", "Close", "Volume", "Turnover"]
def family_suffix(family: str) -> str:
    return "" if family == "xgboost" else "_rf"


def load_market_frame(processed_dir: Path, family: str = "xgboost") -> pd.DataFrame:
    prices = pd.read_parquet(processed_dir / "all_stocks_features.parquet", columns=PRICE_COLUMNS)
    prices["Date"] = pd.to_datetime(prices["Date"])
    # Idempotent: the pipeline already cleans all_stocks_features.parquet, but
    # older artifacts may not be, and the backtest must never see bad rows.
    prices, report = clean_prices(prices)
    prices.attrs["quality_report"] = report
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
