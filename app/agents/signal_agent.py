"""
SignalAgent: the baseline bot. It trades the ML model's calibrated BUY
probability with the same exit discipline the app recommends to people.

Each day, after the close:
  1. exit any holding that trips ExitRulesService (time / stop-loss / signal decay),
  2. rank liquid, un-held stocks by buy probability, keep those >= threshold,
  3. buy the best ones into free slots, sized at exposure * equity / max_positions.
"""

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from app.agents.base import Observation, OrderIntent
from app.constants import THRESHOLD_HIGH
from app.services.exit_rules import ExitRulesService
from app.trading.fees import buy_cost
from app.trading.rules import MIN_BUY_QTY

# Headroom so an order sized at today's close still fits if tomorrow's close is higher.
PRICE_BUFFER = 1.02


class SignalAgent:
    def __init__(
        self,
        name: str = "SignalBot",
        threshold: float = THRESHOLD_HIGH,
        max_positions: int = 5,
        exposure: float = 1.0,
        exit_days: int = 10,
        stop_loss_pct: float = 5.0,
        min_buy_conf: float = 0.45,
    ):
        self.name = name
        self.threshold = threshold
        self.max_positions = max_positions
        self.exposure = exposure
        self.exit_rules = ExitRulesService(exit_days=exit_days, stop_loss_pct=stop_loss_pct, min_buy_conf=min_buy_conf)

    # Overridden by RandomAgent to keep everything else identical.
    def scores(self, obs: Observation) -> pd.Series:
        return obs.market["buy_proba"]

    def passes(self, score: float) -> bool:
        return score >= self.threshold

    def buy_reason(self, symbol: str, score: float, rank: int) -> str:
        return f"Model buy confidence {score:.2f} ≥ {self.threshold:.2f}; ranked #{rank} of today's candidates."

    def exit_conf(self, obs: Observation, symbol: str) -> float:
        conf = obs.market["buy_proba"].get(symbol, np.nan) if "buy_proba" in obs.market else np.nan
        return 1.0 if pd.isna(conf) else float(conf)  # no prediction -> don't treat as decay

    def _exits(self, obs: Observation) -> list[OrderIntent]:
        intents = []
        now = datetime.combine(obs.date, datetime.min.time())
        for symbol, position in obs.portfolio.positions.items():
            price = obs.price(symbol)
            if price is None:
                continue  # didn't trade today; re-check tomorrow
            signal = self.exit_rules.check_exit(
                entry_date=datetime.combine(position.first_buy_date, datetime.min.time()),
                entry_price=position.avg_cost,
                current_price=price,
                current_buy_conf=self.exit_conf(obs, symbol),
                current_date=now,
            )
            if signal.should_exit:
                intents.append(OrderIntent(symbol, "sell", position.qty, f"Exit: {signal.reason}"))
        return intents

    def decide(self, obs: Observation) -> list[OrderIntent]:
        intents = self._exits(obs)
        exiting = {i.symbol for i in intents}
        staying = [s for s in obs.portfolio.positions if s not in exiting]
        slots = self.max_positions - len(staying)
        if slots <= 0 or self.exposure <= 0:
            return intents

        market = obs.market
        eligible = market[market["liquid"].astype(bool) & (market["Close"] > 0)]
        scores = self.scores(obs).reindex(eligible.index).dropna()
        scores = scores[[self.passes(s) for s in scores]] if len(scores) else scores
        scores = scores.drop([s for s in scores.index if s in obs.portfolio.positions], errors="ignore")
        ranked = scores.sort_values(ascending=False).head(slots)

        target = self.exposure * obs.equity / self.max_positions
        budget = obs.portfolio.cash
        for rank, (symbol, score) in enumerate(ranked.items(), 1):
            price = float(eligible.at[symbol, "Close"]) * PRICE_BUFFER
            qty = int(min(target, budget) // price)
            while qty >= MIN_BUY_QTY and buy_cost(price, qty).net_amount > budget:
                qty -= 1
            if qty < MIN_BUY_QTY:
                continue
            budget -= buy_cost(price, qty).net_amount
            intents.append(OrderIntent(symbol, "buy", qty, self.buy_reason(symbol, float(score), rank)))
        return intents


class RandomAgent(SignalAgent):
    """
    Control group: SignalAgent's exact sizing and exits, but picks at random.
    If the model beats this, the edge comes from the predictions, not from
    the trading rules.
    """

    def __init__(self, name: str = "RandomBot", seed: int = 7, **kwargs):
        kwargs.setdefault("min_buy_conf", 0.0)  # no model -> no signal-decay exits
        super().__init__(name=name, threshold=0.0, **kwargs)
        self.rng = np.random.default_rng(seed)

    def scores(self, obs: Observation) -> pd.Series:
        return pd.Series(self.rng.random(len(obs.market)), index=obs.market.index)

    def exit_conf(self, obs: Observation, symbol: str) -> float:
        return 1.0

    def buy_reason(self, symbol: str, score: float, rank: int) -> str:
        return "Random pick (control group for the model)."


class BuyAndHoldAgent:
    """Equal-weight every liquid stock on the first day and never trade again: 'the market'."""

    def __init__(self, name: str = "BuyAndHold", max_names: Optional[int] = None):
        self.name = name
        self.max_names = max_names
        self._bought = False

    def decide(self, obs: Observation) -> list[OrderIntent]:
        if self._bought:
            return []
        market = obs.market
        universe = market[market["liquid"].astype(bool) & (market["Close"] > 0)]
        if self.max_names:
            universe = universe.head(self.max_names)
        if universe.empty:
            return []
        self._bought = True
        per_name = obs.portfolio.cash / len(universe) / PRICE_BUFFER
        intents = []
        for symbol, row in universe.iterrows():
            qty = int(per_name // (row["Close"] * 1.01))
            if qty >= MIN_BUY_QTY:
                intents.append(OrderIntent(symbol, "buy", qty, "Buy-and-hold benchmark."))
        return intents


class CashAgent:
    name = "Cash"

    def decide(self, obs: Observation) -> list[OrderIntent]:
        return []
