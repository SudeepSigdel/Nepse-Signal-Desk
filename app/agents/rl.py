"""
Reinforcement-learning allocator on top of the core-satellite BlendAgent.

The RL policy doesn't pick stocks (≈1,800 daily samples can't teach that for
100+ names). Each day it picks one of a few interpretable allocations -
cash / market basket / model picks - from market-wide state (trend, breadth,
volatility, how many strong signals exist) and its own portfolio state.
Reward: daily log return net of all costs, minus a penalty on new drawdown.

gymnasium / stable-baselines3 are pipeline-only dependencies, imported lazily.
"""

import math
from typing import Optional

import numpy as np
import pandas as pd

from app.agents.base import Observation
from app.agents.blend_agent import BlendAgent
from app.agents.signal_agent import SignalAgent
from app.trading.backtest import MarketData, Simulator

# (basket weight, model-pick weight); the remainder is cash.
ALLOCATIONS: list[tuple[float, float]] = [
    (0.0, 0.0),  # all cash
    (0.0, 0.5),  # picks only
    (0.5, 0.0),  # half market
    (0.5, 0.3),
    (0.8, 0.2),  # classic core-satellite
    (1.0, 0.0),  # fully in the market
]
ALLOCATION_LABELS = [f"{b:.0%} market / {s:.0%} picks / {max(0.0, 1 - b - s):.0%} cash" for b, s in ALLOCATIONS]
CONTEXT_FEATURES = ["ew_ret_1d", "ew_ret_5d", "ew_ret_20d", "ew_vol_20d", "breadth", "n_above_065", "top_decile_proba"]
OBS_SIZE = len(CONTEXT_FEATURES) + 4 + len(ALLOCATIONS)
DRAWDOWN_PENALTY = 0.5


def features(obs: Observation, peak_equity: float, allocation: int, basket: set[str]) -> np.ndarray:
    ctx = obs.context or {}
    scaled = {
        "ew_ret_1d": ctx.get("ew_ret_1d", 0.0) * 50,
        "ew_ret_5d": ctx.get("ew_ret_5d", 0.0) * 20,
        "ew_ret_20d": ctx.get("ew_ret_20d", 0.0) * 10,
        "ew_vol_20d": ctx.get("ew_vol_20d", 0.0) * 50,
        "breadth": ctx.get("breadth", 0.5) * 2 - 1,
        "n_above_065": min(ctx.get("n_above_065", 0.0), 20) / 10,
        "top_decile_proba": (ctx.get("top_decile_proba", 0.0) - 0.5) * 5,
    }
    equity = max(obs.equity, 1e-9)
    basket_value = sum(
        p.qty * (obs.price(s, p.avg_cost) or 0) for s, p in obs.portfolio.positions.items() if s in basket
    )
    invested = equity - obs.portfolio.cash
    portfolio = [
        obs.portfolio.cash / equity,
        basket_value / equity,
        (invested - basket_value) / equity,
        equity / max(peak_equity, 1e-9) - 1,
    ]
    onehot = [1.0 if i == allocation else 0.0 for i in range(len(ALLOCATIONS))]
    vec = np.array([scaled[k] for k in CONTEXT_FEATURES] + portfolio + onehot, dtype=np.float32)
    return np.clip(np.nan_to_num(vec), -5, 5)


class RLAgent:
    """Runs a trained policy (anything with .predict(obs, deterministic=True)) over a BlendAgent."""

    def __init__(self, policy, name: str = "RLBot", satellite: Optional[SignalAgent] = None, start_allocation: int = 4):
        self.name = name
        self.policy = policy
        self.blend = BlendAgent(name=name, satellite=satellite)
        self.allocation = start_allocation
        self.peak = 0.0
        self.blend.set_weights(*ALLOCATIONS[self.allocation])

    def decide(self, obs: Observation):
        self.peak = max(self.peak, obs.equity)
        action, _ = self.policy.predict(features(obs, self.peak, self.allocation, set(self.blend.basket)), deterministic=True)
        self.allocation = int(action)
        self.blend.set_weights(*ALLOCATIONS[self.allocation])
        intents = self.blend.decide(obs)
        note = f" [RL allocation: {ALLOCATION_LABELS[self.allocation]}]"
        return [type(i)(i.symbol, i.side, i.qty, i.reason + note) for i in intents]


def make_env(market: MarketData, start, end, episode_days: int = 250, satellite_params: Optional[dict] = None, seed: int = 0):
    import gymnasium as gym
    from gymnasium import spaces

    days = market.window(start, end)
    if len(days) <= episode_days + 1:
        raise ValueError(f"Training window {start}..{end} has {len(days)} sessions; need > {episode_days + 1}")

    class NepseAllocationEnv(gym.Env):
        metadata = {"render_modes": []}

        def __init__(self):
            super().__init__()
            self.action_space = spaces.Discrete(len(ALLOCATIONS))
            self.observation_space = spaces.Box(-5.0, 5.0, shape=(OBS_SIZE,), dtype=np.float32)
            self._rng = np.random.default_rng(seed)

        def reset(self, *, seed: Optional[int] = None, options=None):
            super().reset(seed=seed)
            if seed is not None:
                self._rng = np.random.default_rng(seed)
            start_index = int(self._rng.integers(0, len(days) - episode_days - 1))
            self.days = days[start_index : start_index + episode_days + 1]
            self.t = 0
            self.sim = Simulator(market)
            self.agent = BlendAgent(name="rl-train", satellite=SignalAgent(**(satellite_params or {})))
            self.allocation = 4
            self.agent.set_weights(*ALLOCATIONS[self.allocation])
            self.obs = self.sim.step(self.days[0])  # first decision happens in step()
            self.peak = self.obs.equity
            return features(self.obs, self.peak, self.allocation, set(self.agent.basket)), {}

        def step(self, action):
            self.allocation = int(action)
            self.agent.set_weights(*ALLOCATIONS[self.allocation])
            # Re-decide today's orders under the new allocation (replaces the queue).
            self.sim.pending = [i for i in self.agent.decide(self.obs) if i.qty > 0]
            prev_equity = self.obs.equity
            prev_dd = 1 - prev_equity / self.peak
            self.t += 1
            self.obs = self.sim.step(self.days[self.t])  # settle, mark to market; no auto-decide
            self.peak = max(self.peak, self.obs.equity)
            dd = 1 - self.obs.equity / self.peak
            reward = math.log(max(self.obs.equity, 1e-9) / max(prev_equity, 1e-9)) - DRAWDOWN_PENALTY * max(0.0, dd - prev_dd)
            done = self.t >= len(self.days) - 1
            return features(self.obs, self.peak, self.allocation, set(self.agent.basket)), float(reward), done, False, {}

    return NepseAllocationEnv()


def load_policy(path) -> Optional[object]:
    try:
        from stable_baselines3 import PPO
    except ImportError:
        return None
    return PPO.load(str(path), device="cpu")


class FixedPolicy:
    """Always the same allocation; for tests and as a sanity baseline."""

    def __init__(self, allocation: int):
        self.allocation = allocation

    def predict(self, obs, deterministic: bool = True):
        return self.allocation, None
