"""
Event-driven daily backtester on the paper-trading engine.

Timeline for each session t (identical to live paper trading):
  1. orders decided after session t-1 fill at session t's close
     (PaperTradingService.settle_pending does the same for queued orders),
  2. the portfolio is marked to market at t's close,
  3. the agent sees only data up to and including t and returns new orders.

Costs and rules come from app/trading (commission tiers, SEBON, DP, CGT,
10-share buy lot). A participation cap limits each fill to a fraction of the
day's traded volume, since a thin NEPSE stock can't absorb a large order.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

from app.agents.base import Agent, Observation, OrderIntent
from app.trading.engine import Portfolio, TradeError, apply_buy, apply_sell, mark_to_market
from app.trading.fees import buy_cost
from app.trading.metrics import summarize
from app.trading.rules import MIN_BUY_QTY

DEFAULT_VOLUME_CAP = 0.10


def add_liquidity(
    frame: pd.DataFrame,
    lookback: int = 120,
    min_days: int = 60,
    min_median_turnover: float = 50_000.0,
    min_median_volume: float = 100.0,
) -> pd.DataFrame:
    """
    Trailing-only version of SignalService.is_liquid_enough: over the last
    `lookback` sessions, enough traded days and a high enough median volume
    and turnover. Uses data up to and including each row, never after it.
    """
    df = frame.sort_values(["Symbol", "Date"]).copy()
    traded = (df["Close"] > 0) & (df["Volume"] > 0)
    turnover = df["Turnover"] if "Turnover" in df else df["Close"] * df["Volume"]
    df["_turnover"] = turnover.where(traded)
    df["_volume"] = df["Volume"].where(traded)
    grouped = df.groupby("Symbol", sort=False)
    days = grouped["_volume"].transform(lambda s: s.rolling(lookback, min_periods=1).count())
    med_turnover = grouped["_turnover"].transform(lambda s: s.rolling(lookback, min_periods=1).median())
    med_volume = grouped["_volume"].transform(lambda s: s.rolling(lookback, min_periods=1).median())
    df["liquid"] = (days >= min_days) & (med_turnover >= min_median_turnover) & (med_volume >= min_median_volume)
    return df.drop(columns=["_turnover", "_volume"])


def market_context(frame: pd.DataFrame) -> pd.DataFrame:
    """Market-wide daily features (equal-weight index, breadth, signal strength), trailing only."""
    df = frame.sort_values(["Symbol", "Date"])
    ret = df.groupby("Symbol")["Close"].pct_change()
    daily = pd.DataFrame({"Date": df["Date"], "ret": ret, "proba": df.get("buy_proba")})
    by_day = daily.groupby("Date")
    ctx = pd.DataFrame(
        {
            "ew_ret_1d": by_day["ret"].mean(),
            "breadth": by_day["ret"].apply(lambda r: float((r > 0).mean()) if r.notna().any() else 0.5),
        }
    )
    if "buy_proba" in df:
        ctx["n_above_055"] = by_day["proba"].apply(lambda p: float((p >= 0.55).sum()))
        ctx["n_above_065"] = by_day["proba"].apply(lambda p: float((p >= 0.65).sum()))
        ctx["top_decile_proba"] = by_day["proba"].apply(
            lambda p: float(p.dropna().quantile(0.9)) if p.notna().any() else 0.0
        )
    index = (1 + ctx["ew_ret_1d"].fillna(0)).cumprod()
    ctx["ew_ret_5d"] = index.pct_change(5)
    ctx["ew_ret_20d"] = index.pct_change(20)
    ctx["ew_vol_20d"] = ctx["ew_ret_1d"].rolling(20).std()
    return ctx.fillna(0.0)


class MarketData:
    """Daily cross-sections, looked up by date in O(1)."""

    def __init__(self, frame: pd.DataFrame):
        df = frame.copy()
        df["Date"] = pd.to_datetime(df["Date"])
        for column, default in (("buy_proba", np.nan), ("sell_proba", np.nan), ("liquid", True)):
            if column not in df:
                df[column] = default
        if "Volume" not in df:
            df["Volume"] = np.inf
        df = df.sort_values(["Date", "Symbol"]).reset_index(drop=True)
        self.dates: list[pd.Timestamp] = [pd.Timestamp(d) for d in pd.unique(df["Date"])]
        self._days = {day: rows.set_index("Symbol") for day, rows in df.groupby("Date", sort=True)}
        self.context = market_context(df)

    def day(self, when) -> pd.DataFrame:
        return self._days[pd.Timestamp(when)]

    def window(self, start=None, end=None) -> list[pd.Timestamp]:
        lo = pd.Timestamp(start) if start is not None else self.dates[0]
        hi = pd.Timestamp(end) if end is not None else self.dates[-1]
        return [d for d in self.dates if lo <= d <= hi]


@dataclass
class BacktestResult:
    agent: str
    equity: pd.Series
    cash: pd.Series
    fills: pd.DataFrame
    skipped: pd.DataFrame
    starting_cash: float
    metrics: dict = field(default_factory=dict)

    def daily_returns(self) -> pd.Series:
        return self.equity.pct_change().dropna()


FILL_COLUMNS = ["date", "symbol", "side", "qty", "price", "fees", "realized_pnl", "reason"]


class Simulator:
    """
    One portfolio stepped a session at a time. run_backtest() drives it for a
    whole window; the RL environment drives it step by step.
    """

    def __init__(self, market: MarketData, starting_cash: float = 1_000_000.0, volume_cap: float = DEFAULT_VOLUME_CAP):
        self.market = market
        self.starting_cash = starting_cash
        self.volume_cap = volume_cap
        self.portfolio = Portfolio(cash=starting_cash)
        self.pending: list[OrderIntent] = []
        self.last_price: dict[str, float] = {}
        self.fills: list[dict] = []
        self.skipped: list[dict] = []
        self.equity_log: list[tuple[pd.Timestamp, float, float]] = []

    def _skip(self, when, intent: OrderIntent, why: str) -> None:
        self.skipped.append({"date": when, "symbol": intent.symbol, "side": intent.side, "qty": intent.qty, "why": why})

    def _settle(self, when: pd.Timestamp, today: pd.DataFrame) -> None:
        trade_day = when.date()
        # Sells first so their proceeds can fund the same session's buys.
        for intent in sorted(self.pending, key=lambda i: i.side != "sell"):
            if intent.symbol not in today.index or not (today.at[intent.symbol, "Close"] > 0):
                self._skip(when, intent, "no trade that session")
                continue
            price = float(today.at[intent.symbol, "Close"])
            volume = today.at[intent.symbol, "Volume"]
            qty = intent.qty
            if np.isfinite(volume):
                qty = min(qty, int(volume * self.volume_cap))
            if intent.side == "sell":
                qty = min(qty, self.portfolio.held_qty(intent.symbol))
                if qty <= 0:
                    self._skip(when, intent, "nothing to sell / no volume")
                    continue
                fill = apply_sell(self.portfolio, intent.symbol, qty, price, trade_day)
            else:
                while qty >= MIN_BUY_QTY and buy_cost(price, qty).net_amount > self.portfolio.cash:
                    qty = int(qty * self.portfolio.cash / buy_cost(price, qty).net_amount)
                if qty < MIN_BUY_QTY:
                    self._skip(when, intent, "below board lot after cash/volume limits")
                    continue
                try:
                    fill = apply_buy(self.portfolio, intent.symbol, qty, price, trade_day)
                except TradeError as exc:
                    self._skip(when, intent, str(exc))
                    continue
            self.fills.append(
                {
                    "date": when, "symbol": fill.symbol, "side": fill.side, "qty": fill.qty, "price": fill.price,
                    "fees": fill.fees.total_fees, "realized_pnl": fill.realized_pnl, "reason": intent.reason,
                }
            )
        self.pending = []

    def step(self, when: pd.Timestamp, agent: Optional[Agent] = None) -> Observation:
        """Settle yesterday's orders at today's close, mark to market, then let the agent decide."""
        today = self.market.day(when)
        self._settle(when, today)
        closes = today["Close"]
        self.last_price.update({s: float(p) for s, p in closes[closes > 0].items()})
        equity, _ = mark_to_market(self.portfolio, self.last_price)
        self.equity_log.append((when, equity, self.portfolio.cash))
        ctx = self.market.context.loc[when].to_dict() if when in self.market.context.index else {}
        obs = Observation(date=when.date(), market=today, portfolio=self.portfolio, equity=equity, context=ctx)
        if agent is not None:
            self.pending = [i for i in agent.decide(obs) if i.qty > 0]
        return obs

    def result(self, agent_name: str, with_ci: bool = True) -> BacktestResult:
        log = pd.DataFrame(self.equity_log, columns=["date", "equity", "cash"]).set_index("date")
        fills = pd.DataFrame(self.fills, columns=FILL_COLUMNS)
        result = BacktestResult(
            agent=agent_name,
            equity=log["equity"],
            cash=log["cash"],
            fills=fills,
            skipped=pd.DataFrame(self.skipped, columns=["date", "symbol", "side", "qty", "why"]),
            starting_cash=self.starting_cash,
        )
        result.metrics = summarize(log["equity"], fills, self.starting_cash, log["cash"], with_ci=with_ci)
        return result


def run_backtest(
    agent: Agent,
    market: MarketData,
    start=None,
    end=None,
    starting_cash: float = 1_000_000.0,
    volume_cap: float = DEFAULT_VOLUME_CAP,
    with_ci: bool = True,
) -> BacktestResult:
    sim = Simulator(market, starting_cash, volume_cap)
    for when in market.window(start, end):
        sim.step(when, agent)
    return sim.result(getattr(agent, "name", type(agent).__name__), with_ci=with_ci)
