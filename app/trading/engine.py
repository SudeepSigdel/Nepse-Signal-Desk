"""
Pure paper-trading engine: cash, positions and fills with NEPSE costs.

No database or web framework here. The API persists these objects, and the
historical backtester / agent environments drive the same functions, so humans
and bots trade under identical rules.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from app.trading.fees import FeeBreakdown, buy_cost, sell_proceeds


@dataclass
class Position:
    symbol: str
    qty: int
    avg_cost: float  # per share, including buy-side fees (WACC)
    first_buy_date: date


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)

    def held_qty(self, symbol: str) -> int:
        position = self.positions.get(symbol)
        return position.qty if position else 0


@dataclass(frozen=True)
class Fill:
    symbol: str
    side: str
    qty: int
    price: float
    trade_date: date
    fees: FeeBreakdown
    realized_pnl: float  # sells only: net proceeds minus cost basis (after CGT)


class TradeError(ValueError):
    """Raised when a fill can't be applied (insufficient cash or shares)."""


def apply_buy(portfolio: Portfolio, symbol: str, qty: int, price: float, trade_date: date) -> Fill:
    fees = buy_cost(price, qty)
    if fees.net_amount > portfolio.cash + 1e-9:
        raise TradeError(f"Insufficient cash for {qty} {symbol} @ {price}: need {fees.net_amount}")

    portfolio.cash = round(portfolio.cash - fees.net_amount, 2)
    position = portfolio.positions.get(symbol)
    if position is None:
        portfolio.positions[symbol] = Position(symbol, qty, fees.net_amount / qty, trade_date)
    else:
        total_cost = position.avg_cost * position.qty + fees.net_amount
        position.qty += qty
        position.avg_cost = total_cost / position.qty
    return Fill(symbol, "buy", qty, price, trade_date, fees, 0.0)


def apply_sell(portfolio: Portfolio, symbol: str, qty: int, price: float, trade_date: date) -> Fill:
    position = portfolio.positions.get(symbol)
    if position is None or qty > position.qty:
        raise TradeError(f"Cannot sell {qty} {symbol}: holding {portfolio.held_qty(symbol)}")

    holding_days = (trade_date - position.first_buy_date).days
    fees = sell_proceeds(price, qty, position.avg_cost, holding_days)
    realized = round(fees.net_amount - position.avg_cost * qty, 2)

    portfolio.cash = round(portfolio.cash + fees.net_amount, 2)
    position.qty -= qty
    if position.qty == 0:
        del portfolio.positions[symbol]
    return Fill(symbol, "sell", qty, price, trade_date, fees, realized)


def mark_to_market(portfolio: Portfolio, prices: dict[str, float]) -> tuple[float, float]:
    """
    Return (equity, unrealized_pnl). Positions without a price are valued at cost.
    Equity is gross market value; exit fees/CGT aren't deducted until a sale.
    """
    market_value = 0.0
    unrealized = 0.0
    for symbol, position in portfolio.positions.items():
        price = prices.get(symbol)
        value = position.qty * price if price is not None else position.qty * position.avg_cost
        market_value += value
        unrealized += value - position.qty * position.avg_cost
    return round(portfolio.cash + market_value, 2), round(unrealized, 2)


def limit_fill_price(
    side: str, limit_price: float, day_low: Optional[float], day_high: Optional[float], close: float
) -> Optional[float]:
    """
    End-of-day fill for a resting limit order, or None if the day's range never
    reached it. Fills at the limit (or better, the close) - never worse than the limit.
    """
    low = day_low if day_low is not None else close
    high = day_high if day_high is not None else close
    if side == "buy":
        if low > limit_price:
            return None
        return min(limit_price, close)
    if high < limit_price:
        return None
    return max(limit_price, close)
