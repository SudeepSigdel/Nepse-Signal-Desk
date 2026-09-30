"""
Let the live trading bots place today's paper orders.

Runs after settle_paper_trades.py in the daily pipeline. Bots get their own
paper accounts (shown with a "bot" badge on the leaderboard); their orders
fill at the next session's close like everyone else's.

Skipped (exit 0) when DATABASE_URL isn't configured, e.g. in CI.
"""

import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
logging.getLogger("app.services.exit_rules").setLevel(logging.WARNING)

from app.config import settings  # noqa: E402


def main() -> int:
    if not settings.database_url:
        print("DATABASE_URL not set; skipping live agents.")
        return 0

    from app.agents.live import build_live_agents, live_market, run_live_agents
    from app.db import SessionLocal
    from app.repositories.model_repository import ModelRepository
    from app.repositories.stock_repository import StockRepository
    from app.services.paper_trading_service import PaperTradingService
    from app.services.price_feed import PriceFeed
    from app.services.signal_service import SignalService

    stocks = StockRepository(settings.data_processed_dir / "all_stocks_features.parquet")
    stocks.load()
    models = ModelRepository(settings.model_dir, settings.data_processed_dir, settings.model_family)
    models.load()
    signals = SignalService(models, stocks)
    signals.warm()

    live_path = PROJECT_ROOT / "outputs" / "agents" / "live_agents.json"
    live_config = json.loads(live_path.read_text()) if live_path.exists() else {}
    trade_date, market, context = live_market(stocks, signals)
    service = PaperTradingService(PriceFeed(stocks))
    with SessionLocal() as db:
        summary = run_live_agents(db, service, build_live_agents(live_config), trade_date, market, context)
    for name, result in summary.items():
        print(f"{name}: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
