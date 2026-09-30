"""Agent interface shared by backtests, the RL environment and live paper accounts."""

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

import pandas as pd

from app.trading.engine import Portfolio


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str  # buy | sell
    qty: int
    reason: str  # shown to learners next to the bot's trade


@dataclass
class Observation:
    """
    What an agent may see when deciding after day `date`'s close.

    `market` is indexed by Symbol with that day's Open/High/Low/Close/Volume,
    `buy_proba` / `sell_proba` (NaN when the model has no prediction) and
    `liquid` (trailing-only liquidity filter). Nothing from later days.
    """

    date: date
    market: pd.DataFrame
    portfolio: Portfolio
    equity: float
    context: dict = field(default_factory=dict)  # market-wide features, e.g. for the RL agent

    def price(self, symbol: str, fallback: float | None = None) -> float | None:
        if symbol in self.market.index:
            close = self.market.at[symbol, "Close"]
            if pd.notna(close) and close > 0:
                return float(close)
        return fallback


class Agent(Protocol):
    name: str

    def decide(self, obs: Observation) -> list[OrderIntent]:
        ...
