"""Tests for the pure paper-trading engine: fees, rules and portfolio accounting."""

from datetime import date, datetime

import pytest

from app.trading import fees, rules
from app.trading.engine import Portfolio, TradeError, apply_buy, apply_sell, limit_fill_price, mark_to_market

D0 = date(2026, 1, 4)


@pytest.mark.parametrize(
    "value, expected_rate",
    [(1_000, 0.0036), (50_000, 0.0036), (50_001, 0.0033), (500_000, 0.0033), (2_000_000, 0.0031),
     (10_000_000, 0.0027), (10_000_001, 0.0024)],
)
def test_commission_tiers(value, expected_rate):
    commission, rate = fees.broker_commission(value)
    assert rate == expected_rate
    assert commission == pytest.approx(max(round(value * expected_rate, 2), fees.MIN_BROKER_COMMISSION))


def test_minimum_commission_applies_to_small_trades():
    assert fees.broker_commission(500)[0] == fees.MIN_BROKER_COMMISSION


def test_buy_cost_itemized():
    b = fees.buy_cost(500.0, 100)  # Rs 50,000 -> 0.36%
    assert b.trade_value == 50_000
    assert b.broker_commission == 180.0
    assert b.sebon_fee == 7.5
    assert b.total_fees == 187.5
    assert b.net_amount == 50_187.5


def test_sell_short_term_cgt_on_profit():
    s = fees.sell_proceeds(600.0, 100, avg_cost=501.875, holding_days=30)
    # 60,000 value: commission 0.33% = 198, SEBON 9, DP 25
    gain = 60_000 - 198 - 9 - 25 - 50_187.5
    assert s.realized_gain == pytest.approx(gain)
    assert s.cgt_rate == fees.CGT_SHORT_TERM_RATE
    assert s.capital_gains_tax == pytest.approx(round(gain * 0.075, 2))
    assert s.net_amount == pytest.approx(60_000 - s.total_fees)


def test_sell_long_term_rate_and_no_cgt_on_loss():
    assert fees.sell_proceeds(600.0, 100, 500.0, 365).cgt_rate == fees.CGT_LONG_TERM_RATE
    loss = fees.sell_proceeds(400.0, 100, 500.0, 10)
    assert loss.capital_gains_tax == 0.0 and loss.cgt_rate == 0.0
    assert loss.realized_gain < 0


def test_buy_then_sell_round_trip_accounting():
    p = Portfolio(cash=100_000)
    buy = apply_buy(p, "NABIL", 100, 500.0, D0)
    assert p.cash == pytest.approx(100_000 - buy.fees.net_amount)
    assert p.positions["NABIL"].avg_cost == pytest.approx(buy.fees.net_amount / 100)

    sell = apply_sell(p, "NABIL", 100, 600.0, date(2026, 2, 3))
    assert "NABIL" not in p.positions
    assert p.cash == pytest.approx(100_000 - buy.fees.net_amount + sell.fees.net_amount)
    assert sell.realized_pnl == pytest.approx(sell.fees.net_amount - buy.fees.net_amount)


def test_average_cost_across_buys_and_partial_sell():
    p = Portfolio(cash=1_000_000)
    b1 = apply_buy(p, "UPPER", 100, 200.0, D0)
    b2 = apply_buy(p, "UPPER", 100, 220.0, date(2026, 1, 5))
    pos = p.positions["UPPER"]
    assert pos.qty == 200
    assert pos.avg_cost == pytest.approx((b1.fees.net_amount + b2.fees.net_amount) / 200)
    assert pos.first_buy_date == D0

    apply_sell(p, "UPPER", 50, 230.0, date(2026, 1, 6))
    assert p.positions["UPPER"].qty == 150
    assert p.positions["UPPER"].avg_cost == pytest.approx(pos.avg_cost)


def test_engine_refuses_overspend_and_short_sale():
    p = Portfolio(cash=1_000)
    with pytest.raises(TradeError):
        apply_buy(p, "NABIL", 10, 500.0, D0)
    with pytest.raises(TradeError):
        apply_sell(p, "NABIL", 10, 500.0, D0)


def test_mark_to_market():
    p = Portfolio(cash=10_000)
    apply_buy(p, "NABIL", 10, 500.0, D0)
    equity, unrealized = mark_to_market(p, {"NABIL": 550.0})
    cost = p.positions["NABIL"].avg_cost * 10
    assert equity == pytest.approx(p.cash + 5_500)
    assert unrealized == pytest.approx(5_500 - cost)
    assert mark_to_market(p, {})[1] == 0.0  # no price -> valued at cost


@pytest.mark.parametrize(
    "side, limit, low, high, close, expected",
    [
        ("buy", 100, 95, 110, 105, 100),  # touched limit intraday
        ("buy", 100, 90, 99, 95, 95),  # closed below limit -> better price
        ("buy", 100, 101, 110, 105, None),  # never reached
        ("sell", 100, 90, 105, 95, 100),
        ("sell", 100, 101, 110, 108, 108),
        ("sell", 100, 80, 99, 95, None),
    ],
)
def test_limit_fill_price(side, limit, low, high, close, expected):
    assert limit_fill_price(side, limit, low, high, close) == expected


@pytest.mark.parametrize(
    "now, is_open",
    [
        (datetime(2026, 9, 29, 11, 0), True),  # Tue open
        (datetime(2026, 9, 29, 14, 59), True),
        (datetime(2026, 9, 29, 15, 0), False),  # closed at 15:00
        (datetime(2026, 9, 29, 10, 59), False),
        (datetime(2026, 9, 27, 12, 0), False),  # Sunday: closed since the April 2026 Mon-Fri switch
        (datetime(2026, 10, 2, 12, 0), True),  # Friday now trades
        (datetime(2025, 9, 28, 12, 0), True),  # Sunday traded in 2025 (Sun-Thu era)
        (datetime(2025, 10, 3, 12, 0), False),  # Friday closed in 2025
    ],
)
def test_market_hours(now, is_open):
    assert rules.is_market_open(now.replace(tzinfo=rules.NEPAL_TZ)) is is_open


def _check(**overrides):
    args = dict(side="buy", order_type="market", qty=10, limit_price=None, prev_close=500.0, held_qty=0,
                available_cash=10_000.0, estimated_buy_total=5_020.0)
    args.update(overrides)
    return rules.validate_order(**args)


@pytest.mark.parametrize(
    "overrides, fragment",
    [
        ({"side": "short"}, "Side"),
        ({"order_type": "stop"}, "Order type"),
        ({"qty": 0}, "positive whole"),
        ({"qty": 5}, "minimum buy lot"),
        ({"side": "sell", "qty": 20, "held_qty": 10}, "short selling"),
        ({"order_type": "limit", "limit_price": None}, "limit price"),
        ({"order_type": "limit", "limit_price": 560.0}, "circuit band"),
        ({"order_type": "limit", "limit_price": 440.0}, "circuit band"),
        ({"estimated_buy_total": 20_000.0}, "Not enough cash"),
    ],
)
def test_validate_order_rejections(overrides, fragment):
    check = _check(**overrides)
    assert not check.ok
    assert fragment in check.reason


def test_validate_order_accepts_valid_orders():
    assert _check().ok
    assert _check(order_type="limit", limit_price=545.0).ok
    assert _check(side="sell", qty=3, held_qty=3, estimated_buy_total=0).ok  # odd-lot exit
    assert rules.circuit_band(500.0) == (450.0, 550.0)
