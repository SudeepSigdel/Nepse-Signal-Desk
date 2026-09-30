"""
NEPSE trading calendar: which weekdays the exchange trades, by era.

NEPSE traded Sunday-Thursday until April 2026, when the government's two-day
weekend moved it to Monday-Friday (last Sunday session 2026-04-05, first
Friday 2026-04-10). In mid-2022 a short-lived two-day weekend left the
history with sessions on both Sundays and Fridays, so that window accepts
Sunday-Friday. Public holidays aren't modelled: a holiday reads as a trading
day, and code that needs the actual sessions uses the price data.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from zoneinfo import ZoneInfo

NEPAL_TZ = ZoneInfo("Asia/Kathmandu")
MARKET_CLOSE_HOUR = 15

# Python weekday numbers: Mon=0 ... Sun=6
SUN_THU = frozenset({6, 0, 1, 2, 3})
MON_FRI = frozenset({0, 1, 2, 3, 4})
SUN_FRI = frozenset({6, 0, 1, 2, 3, 4})

# (first day of era, trading weekdays), in date order.
ERAS: list[tuple[date, frozenset]] = [
    (date(1994, 1, 1), SUN_THU),
    (date(2022, 5, 15), SUN_FRI),
    (date(2022, 10, 1), SUN_THU),
    (date(2026, 4, 6), MON_FRI),
]


def trading_weekdays(day: date) -> frozenset:
    current = ERAS[0][1]
    for start, weekdays in ERAS:
        if day >= start:
            current = weekdays
    return current


def is_trading_weekday(day: date) -> bool:
    return day.weekday() in trading_weekdays(day)


def last_expected_trading_day(now: Optional[datetime] = None) -> date:
    """Most recent trading-weekday session whose close (15:00 NPT) has passed."""
    now = (now or datetime.now(NEPAL_TZ)).astimezone(NEPAL_TZ)
    day = now.date()
    if now.hour < MARKET_CLOSE_HOUR:
        day -= timedelta(days=1)
    while not is_trading_weekday(day):
        day -= timedelta(days=1)
    return day
