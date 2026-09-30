"""
Core-satellite allocation: an equal-weight "core" basket of the most liquid
stocks, a "satellite" of model picks (SignalAgent), and the rest in cash.

`basket_weight` / `signal_weight` can be fixed (a static benchmark such as
80/20) or changed every day by the RL agent. The basket is only traded when a
holding drifts well away from target, or the target weight changes, so
re-allocation doesn't burn money on commissions.
"""

from typing import Optional

import pandas as pd

from app.agents.base import Observation, OrderIntent
from app.agents.signal_agent import PRICE_BUFFER, SignalAgent
from app.trading.engine import Portfolio
from app.trading.fees import buy_cost
from app.trading.rules import MIN_BUY_QTY


class BlendAgent:
    def __init__(
        self,
        name: str = "CoreSatellite",
        basket_weight: float = 0.8,
        signal_weight: float = 0.2,
        basket_size: int = 20,
        refresh_every: int = 120,
        drift_band: float = 0.35,
        satellite: Optional[SignalAgent] = None,
    ):
        self.name = name
        self.basket_weight = basket_weight
        self.signal_weight = signal_weight
        self.basket_size = basket_size
        self.refresh_every = refresh_every
        self.drift_band = drift_band
        self.satellite = satellite or SignalAgent(name=f"{name}-satellite")
        self.basket: list[str] = []
        self.satellite_symbols: set[str] = set()
        self._sessions = 0
        self._last_basket_weight: Optional[float] = None

    def set_weights(self, basket_weight: float, signal_weight: float) -> None:
        self.basket_weight = max(0.0, min(1.0, basket_weight))
        self.signal_weight = max(0.0, min(1.0 - self.basket_weight, signal_weight))

    def _refresh_basket(self, market: pd.DataFrame) -> None:
        liquid = market[market["liquid"].astype(bool) & (market["Close"] > 0)]
        by = "Turnover" if "Turnover" in liquid else "Volume"
        self.basket = list(liquid.sort_values(by, ascending=False).head(self.basket_size).index)

    def _basket_intents(self, obs: Observation) -> list[OrderIntent]:
        refresh = not self.basket or self._sessions % self.refresh_every == 0
        weight_changed = self._last_basket_weight is None or abs(self.basket_weight - self._last_basket_weight) >= 0.05
        old_basket = set(self.basket)
        if refresh:
            self._refresh_basket(obs.market)
        intents = []
        # Names that left the basket (and aren't satellite picks) are sold.
        for symbol in old_basket - set(self.basket):
            held = obs.portfolio.held_qty(symbol)
            if held and symbol not in self.satellite_symbols:
                intents.append(OrderIntent(symbol, "sell", held, "Core basket: no longer among the most liquid stocks."))
        if not self.basket:
            return intents

        target = self.basket_weight * obs.equity / len(self.basket)
        for symbol in self.basket:
            price = obs.price(symbol)
            if price is None or symbol in self.satellite_symbols:
                continue
            held = obs.portfolio.held_qty(symbol)
            value = held * price
            drift = abs(value - target) / target if target > 0 else (1.0 if held else 0.0)
            if not (refresh or weight_changed or drift > self.drift_band):
                continue
            diff = target - value
            if diff > 0:
                qty = int(diff // (price * PRICE_BUFFER))
                if qty >= MIN_BUY_QTY:
                    intents.append(OrderIntent(symbol, "buy", qty, f"Core basket: top-up toward {self.basket_weight:.0%} market exposure."))
            elif held:
                qty = min(held, int(-diff // price) + 1)
                if qty > 0:
                    intents.append(OrderIntent(symbol, "sell", qty, f"Core basket: trim toward {self.basket_weight:.0%} market exposure."))
        self._last_basket_weight = self.basket_weight
        return intents

    def decide(self, obs: Observation) -> list[OrderIntent]:
        self._sessions += 1
        intents = self._basket_intents(obs)
        # Cash the basket is about to spend isn't available to the satellite.
        committed = sum(
            buy_cost(obs.price(i.symbol) * PRICE_BUFFER, i.qty).net_amount for i in intents if i.side == "buy"
        )
        # The satellite sees only its own positions and can't pick basket names.
        sat_view = Portfolio(
            cash=max(0.0, obs.portfolio.cash - committed),
            positions={s: p for s, p in obs.portfolio.positions.items() if s in self.satellite_symbols},
        )
        market = obs.market.copy()
        market.loc[market.index.isin(self.basket), "liquid"] = False
        self.satellite.exposure = self.signal_weight
        sat_obs = Observation(date=obs.date, market=market, portfolio=sat_view, equity=obs.equity, context=obs.context)
        for intent in self.satellite.decide(sat_obs):
            if intent.side == "buy":
                self.satellite_symbols.add(intent.symbol)
            else:
                self.satellite_symbols.discard(intent.symbol)
            intents.append(intent)
        # Drop picks that were sold out or never filled.
        self.satellite_symbols &= set(obs.portfolio.positions) | {i.symbol for i in intents if i.side == "buy"}
        return intents
