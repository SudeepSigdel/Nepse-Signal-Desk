"""NEPSE trading-calendar eras (Sun-Thu → Mon-Fri in April 2026)."""

from datetime import date, datetime

import pytest

from app.trading.calendar import NEPAL_TZ, is_trading_weekday, last_expected_trading_day


@pytest.mark.parametrize(
    "day, trades",
    [
        (date(2025, 10, 5), True),  # Sunday, Sun-Thu era
        (date(2025, 10, 3), False),  # Friday, Sun-Thu era
        (date(2026, 4, 5), True),  # last Sunday session in the data
        (date(2026, 4, 10), True),  # first Friday session in the data
        (date(2026, 4, 12), False),  # Sunday after the switch
        (date(2026, 9, 26), False),  # Saturday
        (date(2022, 6, 3), True),  # Friday in the 2022 two-day-weekend window
        (date(2022, 6, 19), True),  # Sunday in that window also traded
    ],
)
def test_trading_weekdays_by_era(day, trades):
    assert is_trading_weekday(day) is trades


def test_last_expected_trading_day_crosses_the_switch():
    # Sunday 2026-04-12 morning: the previous session is Friday 04-10.
    assert last_expected_trading_day(datetime(2026, 4, 12, 9, 0, tzinfo=NEPAL_TZ)) == date(2026, 4, 10)
    # Monday 2026-04-06 before close: previous session was Sunday 04-05 (old era).
    assert last_expected_trading_day(datetime(2026, 4, 6, 12, 0, tzinfo=NEPAL_TZ)) == date(2026, 4, 5)
