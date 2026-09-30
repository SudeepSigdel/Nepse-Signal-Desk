"""
Settle pending paper-trading orders against the latest daily bars.

Runs as the last step of the daily pipeline, after the scraper and feature
pipeline have refreshed data/processed/all_stocks_features.parquet:
  - pending market orders fill at the session close,
  - pending limit orders fill if the day's high/low reached the limit, else expire,
  - every account gets an equity snapshot for the leaderboard / equity curve.

Skipped (exit 0) when DATABASE_URL isn't configured, e.g. in CI.

Usage:
    python automation/settle_paper_trades.py [--date YYYY-MM-DD]
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings  # noqa: E402


def load_bars(features_path: Path, trade_date: date | None):
    from app.services.paper_trading_service import Bar

    df = pd.read_parquet(features_path, columns=["Symbol", "Date", "Close", "High", "Low"])
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    day = pd.Timestamp(trade_date) if trade_date else df["Date"].max()
    rows = df[df["Date"] == day]

    def num(value):
        return None if pd.isna(value) else float(value)

    bars = {
        row.Symbol: Bar(close=float(row.Close), high=num(row.High), low=num(row.Low))
        for row in rows.itertuples()
        if pd.notna(row.Close)
    }
    return day.date(), bars


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default="", help="Session to settle (default: latest date in the data).")
    args = parser.parse_args()

    if not settings.database_url:
        print("DATABASE_URL not set; skipping paper-trade settlement.")
        return 0

    from app.db import SessionLocal
    from app.repositories.stock_repository import StockRepository
    from app.services.paper_trading_service import PaperTradingService
    from app.services.price_feed import PriceFeed

    features_path = settings.data_processed_dir / "all_stocks_features.parquet"
    trade_date, bars = load_bars(features_path, date.fromisoformat(args.date) if args.date else None)
    if not bars:
        print(f"No bars found for {trade_date}; nothing to settle.")
        return 0

    repository = StockRepository(features_path)
    repository.load()
    service = PaperTradingService(PriceFeed(repository))  # EOD prices only
    with SessionLocal() as db:
        stats = service.settle_pending(db, trade_date, bars)
    print(f"Settled paper trades for {trade_date} ({len(bars)} symbols): {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
