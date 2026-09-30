"""Tests for the event-driven backtester and the baseline agents (synthetic data)."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.agents.base import Observation, OrderIntent
from app.agents.data import adjust_for_corporate_actions
from app.agents.signal_agent import BuyAndHoldAgent, CashAgent, RandomAgent, SignalAgent
from app.trading.backtest import MarketData, Simulator, add_liquidity, run_backtest
from app.trading.fees import buy_cost, sell_proceeds


def frame(prices: dict[str, list[float]], proba: dict[str, list[float]] | None = None, volume=1e6, start="2026-01-01"):
    days = pd.bdate_range(start, periods=len(next(iter(prices.values()))))
    rows = []
    for sym, closes in prices.items():
        for i, (d, c) in enumerate(zip(days, closes)):
            rows.append({"Symbol": sym, "Date": d, "Open": c, "High": c, "Low": c, "Close": c, "Volume": volume,
                         "buy_proba": (proba or {}).get(sym, [np.nan] * len(closes))[i], "liquid": True})
    return pd.DataFrame(rows)


class Scripted:
    """Buys on a given day; used to probe timing and costs."""

    name = "Scripted"

    def __init__(self, plan: dict[int, list[OrderIntent]]):
        self.plan, self.day = plan, -1

    def decide(self, obs: Observation):
        self.day += 1
        return self.plan.get(self.day, [])


def test_orders_fill_at_next_close_not_same_day():
    # Price jumps the day after the decision: a same-day fill would capture it.
    market = MarketData(frame({"AAA": [100, 150, 150]}))
    result = run_backtest(Scripted({0: [OrderIntent("AAA", "buy", 100, "test")]}), market, starting_cash=100_000)
    fill = result.fills.iloc[0]
    assert fill["date"] == market.dates[1] and fill["price"] == 150
    assert result.equity.iloc[-1] < 100_000  # bought at 150, still 150: only fees lost


def test_round_trip_costs_match_fee_engine():
    market = MarketData(frame({"AAA": [100, 100, 110, 110]}))
    agent = Scripted({0: [OrderIntent("AAA", "buy", 100, "b")], 1: [OrderIntent("AAA", "sell", 100, "s")]})
    result = run_backtest(agent, market, starting_cash=100_000)
    buy = buy_cost(100, 100)
    sell = sell_proceeds(110, 100, buy.net_amount / 100, holding_days=1)
    assert result.equity.iloc[-1] == pytest.approx(100_000 - buy.net_amount + sell.net_amount)
    assert result.fills["fees"].sum() == pytest.approx(buy.total_fees + sell.total_fees)


def test_volume_cap_and_board_lot():
    market = MarketData(frame({"AAA": [100] * 3}, volume=500))  # 10% cap -> 50 shares max
    result = run_backtest(Scripted({0: [OrderIntent("AAA", "buy", 1000, "b")]}), market, starting_cash=1_000_000)
    assert result.fills["qty"].tolist() == [50]

    thin = MarketData(frame({"AAA": [100] * 3}, volume=50))  # cap -> 5 < board lot
    result = run_backtest(Scripted({0: [OrderIntent("AAA", "buy", 1000, "b")]}), thin, starting_cash=1_000_000)
    assert result.fills.empty and "board lot" in result.skipped["why"].iloc[0]


def test_buys_shrink_to_available_cash():
    market = MarketData(frame({"AAA": [100] * 3}))
    result = run_backtest(Scripted({0: [OrderIntent("AAA", "buy", 10_000, "b")]}), market, starting_cash=50_000)
    assert result.fills["qty"].iloc[0] < 500 and result.equity.iloc[-1] > 0


def test_signal_agent_ranks_thresholds_and_sizes():
    probs = {"AAA": [0.9] * 4, "BBB": [0.7] * 4, "CCC": [0.66] * 4, "DDD": [0.5] * 4}
    market = MarketData(frame({s: [100] * 4 for s in probs}, probs))
    agent = SignalAgent(max_positions=2)
    sim = Simulator(market, 100_000)
    obs = sim.step(market.dates[0], agent)
    intents = agent.decide(obs)
    assert [i.symbol for i in intents] == ["AAA", "BBB"]  # top-2 above 0.65, DDD below threshold
    assert all(i.qty * 100 <= 100_000 / 2 for i in intents)
    assert "0.90" in intents[0].reason


def test_signal_agent_exits_on_stop_loss_and_time():
    closes = [100, 100, 100, 94, 94, 94] + [94] * 12
    market = MarketData(frame({"AAA": closes}, {"AAA": [0.9] + [np.nan] * (len(closes) - 1)}))
    result = run_backtest(SignalAgent(max_positions=1), market, starting_cash=100_000)
    sells = result.fills[result.fills["side"] == "sell"]
    assert len(sells) == 1
    assert "stop" in sells["reason"].iloc[0].lower()
    assert sells["date"].iloc[0] == market.dates[4]  # decided after day 3's drop, filled next close


def test_random_agent_is_reproducible():
    probs = {s: [0.5] * 30 for s in "ABCDEFGH"}
    market = MarketData(frame({s: list(100 + np.arange(30)) for s in probs}, probs))
    a = run_backtest(RandomAgent(seed=1), market).fills
    b = run_backtest(RandomAgent(seed=1), market).fills
    pd.testing.assert_frame_equal(a, b)


def test_buy_and_hold_and_cash_benchmarks():
    market = MarketData(frame({"AAA": [100, 100, 120], "BBB": [50, 50, 60]}))
    bh = run_backtest(BuyAndHoldAgent(), market, starting_cash=100_000)
    assert set(bh.fills["symbol"]) == {"AAA", "BBB"}
    assert bh.metrics["total_return_pct"] > 15  # +20% prices minus buy costs
    cash = run_backtest(CashAgent(), market, starting_cash=100_000)
    assert cash.metrics["total_return_pct"] == 0 and cash.metrics["trades"] == 0


def test_liquidity_filter_is_trailing_only():
    df = frame({"AAA": [100] * 10}, volume=1000)
    df.loc[df.index[-1], "Volume"] = 0  # a future dry day must not affect earlier rows
    out = add_liquidity(df.drop(columns="liquid"), lookback=5, min_days=3, min_median_turnover=0, min_median_volume=1)
    assert out["liquid"].tolist()[:3] == [False, False, True]


def test_corporate_action_gaps_are_back_adjusted():
    df = frame({"AAA": [100, 102, 85, 86, 90]})
    adjusted, gaps = adjust_for_corporate_actions(df)
    assert gaps == 1
    returns = adjusted["Close"].pct_change().dropna()
    assert returns.abs().max() < 0.105
    assert adjusted["Close"].iloc[-1] == 90  # latest prices untouched
