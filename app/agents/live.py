"""
Live paper trading for bots: the same orders, fills and fees as human users.

After each daily settlement, every live bot looks at the newest session
(prices + the deployed model's probabilities), decides, and places market
orders through PaperTradingService. The orders sit pending and fill at the
next session's close, exactly like a person's after-hours order, and each one
carries the bot's reason in PaperOrder.note.
"""

from datetime import date
from typing import Iterable

import pandas as pd
from sqlalchemy.orm import Session

from app.agents.base import Observation
from app.agents.signal_agent import SignalAgent
from app.db_models import PaperAccount, User
from app.repositories.stock_repository import StockRepository
from app.services.paper_trading_service import PaperTradingService
from app.services.signal_service import SignalService
from app.trading.backtest import add_liquidity, market_context
from app.trading.engine import Portfolio, mark_to_market

SYSTEM_EMAIL = "agents@nepse-signal-desk.local"  # no password / Google id: can't log in
BOT_STARTING_CASH = 1_000_000.0
LOOKBACK_SESSIONS = 200


def live_market(stocks: StockRepository, signals: SignalService) -> tuple[date, pd.DataFrame, dict]:
    """Latest session's cross-section in the same shape backtests use."""
    df = stocks.features_df
    recent_dates = sorted(df["Date"].unique())[-LOOKBACK_SESSIONS:]
    recent = df[df["Date"].isin(recent_dates)][["Symbol", "Date", "Close", "Volume", "Turnover"]]
    recent = add_liquidity(recent)
    latest = recent_dates[-1]
    today = recent[recent["Date"] == latest].set_index("Symbol")
    today["buy_proba"] = [signals.compute_confidence(s) for s in today.index]
    today["sell_proba"] = [signals.compute_sell_confidence(s) for s in today.index]
    today[["buy_proba", "sell_proba"]] = today[["buy_proba", "sell_proba"]].astype(float)
    context_frame = recent.merge(today[["buy_proba"]].reset_index(), on="Symbol", how="left")
    context_frame.loc[context_frame["Date"] != latest, "buy_proba"] = float("nan")
    context = market_context(context_frame).iloc[-1].to_dict()
    return pd.Timestamp(latest).date(), today, context


def ensure_bot_account(db: Session, service: PaperTradingService, name: str) -> PaperAccount:
    user = db.query(User).filter(User.email == SYSTEM_EMAIL).first()
    if user is None:
        user = User(email=SYSTEM_EMAIL, hashed_password=None)
        db.add(user)
        db.commit()
        db.refresh(user)
    account = (
        db.query(PaperAccount)
        .filter(PaperAccount.user_id == user.id, PaperAccount.name == name, PaperAccount.is_agent.is_(True))
        .first()
    )
    if account is None:
        account = PaperAccount(
            user_id=user.id, name=name, starting_cash=BOT_STARTING_CASH, cash=BOT_STARTING_CASH, is_agent=True
        )
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def build_live_agents(live_config: dict) -> list:
    agents = [SignalAgent(name="SignalBot")]
    if live_config.get("signal_config"):
        agents.append(SignalAgent(name="TunedSignalBot", **live_config["signal_config"]))
    return agents


def run_live_agents(
    db: Session, service: PaperTradingService, agents: Iterable, trade_date: date, market: pd.DataFrame, context: dict
) -> dict:
    """Place today's bot orders. Idempotent: a bot with pending orders already decided today."""
    summary = {}
    prices = {s: float(p) for s, p in market["Close"].items() if pd.notna(p) and p > 0}
    for agent in agents:
        account = ensure_bot_account(db, service, agent.name)
        if any(o.status == "pending" for o in account.orders):
            summary[agent.name] = {"skipped": "orders already pending"}
            continue
        portfolio = service._portfolio(account)
        view = Portfolio(cash=service.available_cash(account), positions=portfolio.positions)
        equity, _ = mark_to_market(portfolio, prices)
        obs = Observation(date=trade_date, market=market, portfolio=view, equity=equity, context=context)
        placed = []
        for intent in agent.decide(obs):
            order = service.place_order(db, account, intent.symbol, intent.side, "market", intent.qty, note=intent.reason)
            placed.append({"symbol": order.symbol, "side": order.side, "qty": order.qty, "status": order.status})
        summary[agent.name] = {"equity": equity, "orders": placed}
    return summary
