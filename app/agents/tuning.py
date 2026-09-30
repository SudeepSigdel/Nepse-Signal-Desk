"""
Walk-forward tuning: choose an agent's settings using only the past.

For each test fold (a calendar year of out-of-sample predictions), every
config in the grid is backtested on the preceding `train_years`; the best by
Sharpe trades the test fold. The stitched test folds form one continuous
portfolio - positions carry over, only the rules change - so the result is an
honest estimate of "tune on history, then trade the unknown next year".
"""

import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from app.agents.base import Observation
from app.agents.signal_agent import SignalAgent
from app.trading.backtest import MarketData, run_backtest

DEFAULT_GRID = {
    "threshold": [0.60, 0.65, 0.70, 0.75],
    "exit_days": [10, 20, 30],
    "stop_loss_pct": [5.0, 10.0],
}


@dataclass(frozen=True)
class Fold:
    fold: int
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def load_folds(fold_config_path: Path) -> list[Fold]:
    config = json.loads(Path(fold_config_path).read_text())
    return [
        Fold(int(f["fold"]), pd.Timestamp(f["test_start"]), pd.Timestamp(f["test_end"]))
        for f in config["folds"]
    ]


def grid_configs(grid: dict = DEFAULT_GRID) -> list[dict]:
    keys = list(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def config_label(config: dict) -> str:
    return (
        f"threshold {config['threshold']:.2f}, exit after {config['exit_days']}d, "
        f"stop-loss {config['stop_loss_pct']:.0f}%"
    )


class ScheduledAgent:
    """Delegates to the SignalAgent whose config was chosen for the current fold."""

    def __init__(self, schedule: list[tuple[pd.Timestamp, SignalAgent]], name: str = "TunedSignalBot"):
        self.name = name
        self.schedule = sorted(schedule, key=lambda item: item[0])

    def active(self, when) -> Optional[SignalAgent]:
        current = None
        for start, agent in self.schedule:
            if pd.Timestamp(when) >= start:
                current = agent
        return current

    def decide(self, obs: Observation):
        agent = self.active(obs.date)
        return agent.decide(obs) if agent else []


def score(metrics: dict) -> float:
    # Sharpe rewards return per unit of risk; a config that never trades scores 0, not -inf.
    return float(metrics.get("sharpe", 0.0)) if metrics.get("trades", 0) else 0.0


def walk_forward(
    market: MarketData,
    folds: list[Fold],
    grid: dict = DEFAULT_GRID,
    train_years: int = 3,
    min_train_days: int = 200,
    agent_factory: Callable[..., SignalAgent] = SignalAgent,
    log: Callable[[str], None] = print,
) -> tuple[ScheduledAgent, list[dict]]:
    """Return the scheduled agent plus a per-fold record of what was chosen and why."""
    configs = grid_configs(grid)
    schedule, choices = [], []
    for fold in folds:
        train_start = fold.test_start - pd.DateOffset(years=train_years)
        train_days = market.window(train_start, fold.test_start - pd.Timedelta(days=1))
        if len(train_days) < min_train_days:
            continue
        ranked = []
        for config in configs:
            metrics = run_backtest(agent_factory(**config), market, train_days[0], train_days[-1], with_ci=False).metrics
            ranked.append((score(metrics), config, metrics))
        best_score, best, best_metrics = max(ranked, key=lambda item: item[0])
        schedule.append((fold.test_start, agent_factory(name="TunedSignalBot", **best)))
        choices.append(
            {
                "fold": fold.fold,
                "test_start": fold.test_start.date().isoformat(),
                "test_end": fold.test_end.date().isoformat(),
                "train_start": train_days[0].date().isoformat(),
                "train_end": train_days[-1].date().isoformat(),
                "config": best,
                "label": config_label(best),
                "train_sharpe": round(best_score, 3),
                "train_return_pct": best_metrics.get("total_return_pct"),
            }
        )
        log(f"  fold {fold.fold}: {config_label(best)} (train Sharpe {best_score:.2f})")
    return ScheduledAgent(schedule), choices
