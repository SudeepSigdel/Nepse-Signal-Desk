"""NEPSE market rules applied to simulated orders."""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from app.trading.calendar import is_trading_weekday

NEPAL_TZ = ZoneInfo("Asia/Kathmandu")
MARKET_OPEN = time(11, 0)
MARKET_CLOSE = time(15, 0)
CIRCUIT_LIMIT = 0.10  # daily price band around the previous close
MIN_BUY_QTY = 10  # board lot; sells may be any whole quantity held (odd-lot exits)

SIDES = ("buy", "sell")
ORDER_TYPES = ("market", "limit")


def nepal_now() -> datetime:
    return datetime.now(NEPAL_TZ)


def is_market_open(now: Optional[datetime] = None) -> bool:
    """Regular session check (Mon-Fri since April 2026). Public holidays aren't known, so a holiday reads as open."""
    now = (now or nepal_now()).astimezone(NEPAL_TZ)
    return is_trading_weekday(now.date()) and MARKET_OPEN <= now.time() < MARKET_CLOSE


def circuit_band(prev_close: float) -> tuple[float, float]:
    return round(prev_close * (1 - CIRCUIT_LIMIT), 2), round(prev_close * (1 + CIRCUIT_LIMIT), 2)


@dataclass(frozen=True)
class OrderCheck:
    ok: bool
    reason: str = ""


def validate_order(
    side: str,
    order_type: str,
    qty: int,
    limit_price: Optional[float],
    prev_close: Optional[float],
    held_qty: int,
    available_cash: float,
    estimated_buy_total: float,
) -> OrderCheck:
    """
    Check an order before it is filled or queued. Reasons are written for
    learners, since a rejected order is part of the lesson.
    """
    if side not in SIDES:
        return OrderCheck(False, f"Side must be one of {SIDES}.")
    if order_type not in ORDER_TYPES:
        return OrderCheck(False, f"Order type must be one of {ORDER_TYPES}.")
    if not isinstance(qty, int) or qty <= 0:
        return OrderCheck(False, "Quantity must be a positive whole number of shares.")
    if side == "buy" and qty < MIN_BUY_QTY:
        return OrderCheck(False, f"NEPSE's minimum buy lot is {MIN_BUY_QTY} shares.")
    if side == "sell" and qty > held_qty:
        return OrderCheck(
            False, f"You hold {held_qty} shares; short selling isn't allowed on NEPSE."
        )

    if order_type == "limit":
        if limit_price is None or limit_price <= 0:
            return OrderCheck(False, "A limit order needs a positive limit price.")
        if prev_close:
            low, high = circuit_band(prev_close)
            if not low <= limit_price <= high:
                return OrderCheck(
                    False,
                    f"Limit {limit_price:.2f} is outside today's ±{CIRCUIT_LIMIT:.0%} circuit band "
                    f"({low:.2f}–{high:.2f}).",
                )

    if side == "buy" and estimated_buy_total > available_cash:
        return OrderCheck(
            False,
            f"Not enough cash: this order needs about Rs {estimated_buy_total:,.2f} including fees, "
            f"you have Rs {available_cash:,.2f} available.",
        )
    return OrderCheck(True)
