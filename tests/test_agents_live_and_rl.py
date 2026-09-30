"""Tests for walk-forward scheduling, core-satellite blending, live bots and the RL env."""

from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.agents.blend_agent import BlendAgent
from app.agents.live import SYSTEM_EMAIL, build_live_agents, ensure_bot_account, run_live_agents
from app.agents.rl import ALLOCATIONS, OBS_SIZE, FixedPolicy, RLAgent
from app.agents.signal_agent import SignalAgent
from app.agents.tuning import Fold, ScheduledAgent, walk_forward
from app.db_models import PaperOrder, User
from app.repositories.stock_repository import StockRepository
from app.services.paper_trading_service import PaperTradingService
from app.services.price_feed import PriceFeed
from app.trading.backtest import MarketData, run_backtest
from app.trading.rules import NEPAL_TZ
from tests.test_backtest import frame


def trending_market(days=400, n=6, seed=0):
    rng = np.random.default_rng(seed)
    prices, probs = {}, {}
    for i in range(n):
        steps = rng.normal(0.001 * (i - 2), 0.01, days)
        prices[f"S{i}"] = list(100 * np.exp(np.cumsum(steps)))
        probs[f"S{i}"] = list(np.clip(0.5 + 0.1 * (i - 2) + rng.normal(0, 0.05, days), 0, 1))
    return MarketData(frame(prices, probs, start="2020-01-01"))


def test_scheduled_agent_switches_config_by_date():
    early, late = SignalAgent(threshold=0.9), SignalAgent(threshold=0.1)
    agent = ScheduledAgent([(pd.Timestamp("2021-01-01"), late), (pd.Timestamp("2020-01-01"), early)])
    assert agent.active("2019-06-01") is None
    assert agent.active("2020-06-01") is early
    assert agent.active("2021-06-01") is late


def test_walk_forward_picks_configs_from_the_past_only():
    market = trending_market()
    folds = [Fold(1, market.dates[250], market.dates[-1])]
    agent, choices = walk_forward(market, folds, grid={"threshold": [0.6, 0.9], "exit_days": [10], "stop_loss_pct": [5.0]},
                                  train_years=1, min_train_days=100, log=lambda _: None)
    assert len(choices) == 1
    assert choices[0]["train_end"] < choices[0]["test_start"]
    result = run_backtest(agent, market, start=folds[0].test_start)
    assert result.metrics["days"] > 0


def test_blend_agent_holds_basket_and_satellite_without_overlap():
    market = trending_market()
    blend = BlendAgent(basket_weight=0.6, signal_weight=0.3, basket_size=3, satellite=SignalAgent(threshold=0.55, max_positions=2))
    result = run_backtest(blend, market, starting_cash=1_000_000)
    buys = result.fills[result.fills["side"] == "buy"]
    core = set(buys[buys["reason"].str.startswith("Core basket")]["symbol"])
    picks = set(buys[buys["reason"].str.startswith("Model")]["symbol"])
    assert core and picks and not core & picks
    assert 40 < result.metrics["avg_exposure_pct"] < 100


def test_rl_agent_follows_its_policy_allocation():
    market = trending_market()
    cash_only = run_backtest(RLAgent(FixedPolicy(0)), market)
    assert cash_only.metrics["trades"] == 0
    full = run_backtest(RLAgent(FixedPolicy(len(ALLOCATIONS) - 1)), market)
    assert full.metrics["avg_exposure_pct"] > 80
    assert "[RL allocation: 100% market" in full.fills["reason"].iloc[0]


def test_rl_env_contract_and_reward():
    gym = pytest.importorskip("gymnasium")
    from gymnasium.utils.env_checker import check_env

    from app.agents.rl import make_env

    market = trending_market()
    env = make_env(market, market.dates[0], market.dates[-1], episode_days=60)
    check_env(env, skip_render_check=True)
    obs, _ = env.reset(seed=3)
    assert obs.shape == (OBS_SIZE,) and env.action_space.n == len(ALLOCATIONS)
    total, done = 0.0, False
    first_equity = env.obs.equity
    while not done:
        obs, reward, done, _, _ = env.step(0)  # all cash: no trades, no fees
        total += reward
    assert total == pytest.approx(0.0) and env.obs.equity == pytest.approx(first_equity)


# ─── Live bots ────────────────────────────────────────────


@pytest.fixture
def live_setup(db_session):
    repo = StockRepository(Path("unused.parquet"))
    repo.load_frame(pd.DataFrame({
        "Symbol": ["AAA", "BBB"] * 3,
        "Date": pd.to_datetime(["2026-09-27"] * 2 + ["2026-09-28"] * 2 + ["2026-09-29"] * 2),
        "Close": [100.0, 50.0] * 3, "High": [101.0, 51.0] * 3, "Low": [99.0, 49.0] * 3,
    }))
    service = PaperTradingService(PriceFeed(repo), clock=lambda: datetime(2026, 9, 29, 18, 0, tzinfo=NEPAL_TZ))
    market = pd.DataFrame(
        {"Close": [100.0, 50.0], "Volume": [1e5, 1e5], "liquid": [True, True], "buy_proba": [0.8, 0.3], "sell_proba": [0.1, 0.1]},
        index=pd.Index(["AAA", "BBB"], name="Symbol"),
    )
    return db_session, service, market


def test_live_bots_trade_with_notes_and_are_idempotent(live_setup):
    db, service, market = live_setup
    agents = build_live_agents({"signal_config": {"threshold": 0.7, "exit_days": 20, "stop_loss_pct": 10.0}})
    assert [a.name for a in agents] == ["SignalBot", "TunedSignalBot"]

    summary = run_live_agents(db, service, agents, date(2026, 9, 29), market, {})
    assert summary["SignalBot"]["orders"] == [{"symbol": "AAA", "side": "buy", "qty": summary["SignalBot"]["orders"][0]["qty"], "status": "pending"}]
    orders = db.query(PaperOrder).all()
    assert all("Model buy confidence 0.80" in o.note for o in orders)

    again = run_live_agents(db, service, agents, date(2026, 9, 29), market, {})
    assert again["SignalBot"] == {"skipped": "orders already pending"}
    assert db.query(PaperOrder).count() == len(orders)

    bot_user = db.query(User).filter(User.email == SYSTEM_EMAIL).one()
    assert bot_user.hashed_password is None and bot_user.google_sub is None  # cannot log in
    assert ensure_bot_account(db, service, "SignalBot").is_agent
