"""Tests for the paper-trading service and price feed (SQLite, no network)."""

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from app.db_models import PaperEquitySnapshot, User
from app.repositories.stock_repository import StockRepository
from app.services.paper_trading_service import Bar, PaperTradingService
from app.services.price_feed import PriceFeed
from app.trading.rules import NEPAL_TZ

TUE_BEFORE_OPEN = datetime(2026, 9, 29, 9, 0, tzinfo=NEPAL_TZ)
TUE_OPEN = datetime(2026, 9, 29, 12, 0, tzinfo=NEPAL_TZ)
TUE_AFTER_CLOSE = datetime(2026, 9, 29, 16, 0, tzinfo=NEPAL_TZ)
TUE = date(2026, 9, 29)
WED = date(2026, 9, 30)


def _repo():
    repo = StockRepository(Path("unused.parquet"))
    repo.features_df = pd.DataFrame(
        {
            "Symbol": ["NABIL", "NABIL", "UPPER", "UPPER"],
            "Date": pd.to_datetime(["2026-09-27", "2026-09-28"] * 2),
            "Close": [490.0, 500.0, 195.0, 200.0],
            "High": [495.0, 505.0, 198.0, 202.0],
            "Low": [485.0, 495.0, 190.0, 198.0],
        }
    )
    repo.all_symbols = ["NABIL", "UPPER"]
    return repo


LIVE_ROWS = [
    {"symbol": "NABIL", "lastTradedPrice": 510.0, "previousClose": 500.0, "highPrice": 512.0,
     "lowPrice": 498.0, "lastUpdatedDateTime": "2026-09-29T12:00:00"},
]


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def user(db_session):
    user = User(email="trader@example.com", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    return user


def _service(clock, live=True, live_rows=LIVE_ROWS):
    def market_open(now=None):
        now = now or clock()
        return 11 <= now.hour < 15

    feed = PriceFeed(
        _repo(),
        nepse_api_url="http://nepse-api" if live else "",
        market_open=lambda: market_open(clock()),
        http_get=lambda url: live_rows,
    )
    return PaperTradingService(feed, clock=clock, market_open=market_open)


def test_eod_quote_uses_latest_close_as_next_session_band():
    quote = PriceFeed(_repo()).get_quote("nabil")
    assert (quote.source, quote.price, quote.prev_close) == ("eod", 500.0, 490.0)
    assert (quote.circuit_low, quote.circuit_high) == (450.0, 550.0)
    assert PriceFeed(_repo()).get_quote("NOPE") is None


def test_live_quote_falls_back_to_eod_when_server_fails():
    def broken(url):
        raise ConnectionError("down")

    feed = PriceFeed(_repo(), "http://nepse-api", market_open=lambda: True, http_get=broken)
    assert feed.get_quote("NABIL").source == "eod"


def test_market_order_fills_live_during_session(db_session, user):
    service = _service(Clock(TUE_OPEN))
    account = service.create_account(db_session, user, "Main", 100_000)

    order = service.place_order(db_session, account, "nabil", "buy", "market", 20)

    assert (order.status, order.fill_price, order.price_source) == ("filled", 510.0, "live")
    fees = json.loads(order.fees_json)
    assert account.cash == pytest.approx(100_000 - fees["net_amount"])
    assert account.positions[0].qty == 20


def test_order_outside_hours_waits_then_settles_at_close(db_session, user):
    clock = Clock(TUE_BEFORE_OPEN)
    service = _service(clock)
    account = service.create_account(db_session, user, "Main", 100_000)

    order = service.place_order(db_session, account, "NABIL", "buy", "market", 20)
    assert order.status == "pending"
    assert order.reserved_cash > 20 * 550  # reserved at the circuit ceiling incl. fees
    assert service.available_cash(account) == pytest.approx(100_000 - order.reserved_cash)
    assert account.cash == 100_000

    stats = service.settle_pending(db_session, TUE, {"NABIL": Bar(close=505.0, high=508.0, low=499.0)})
    assert stats["filled"] == 1
    assert (order.status, order.fill_price, order.price_source, order.reserved_cash) == ("filled", 505.0, "eod", 0.0)
    snap = db_session.query(PaperEquitySnapshot).one()
    assert snap.date == TUE and snap.equity == pytest.approx(account.cash + 20 * 505.0)


def test_orders_after_close_wait_for_next_session(db_session, user):
    service = _service(Clock(TUE_AFTER_CLOSE))
    account = service.create_account(db_session, user, "Main", 100_000)
    order = service.place_order(db_session, account, "NABIL", "buy", "market", 10)

    stats = service.settle_pending(db_session, TUE, {"NABIL": Bar(close=505.0)})
    assert (stats["waiting"], order.status) == (1, "pending")

    service.settle_pending(db_session, WED, {"NABIL": Bar(close=507.0)})
    assert (order.status, order.fill_price) == ("filled", 507.0)


def test_limit_orders_fill_or_expire(db_session, user):
    service = _service(Clock(TUE_BEFORE_OPEN))
    account = service.create_account(db_session, user, "Main", 100_000)
    hit = service.place_order(db_session, account, "NABIL", "buy", "limit", 10, limit_price=498.0)
    miss = service.place_order(db_session, account, "UPPER", "buy", "limit", 10, limit_price=190.0)

    service.settle_pending(
        db_session, TUE, {"NABIL": Bar(close=502.0, high=506.0, low=497.0), "UPPER": Bar(close=201.0, low=196.0)}
    )

    assert (hit.status, hit.fill_price) == ("filled", 498.0)
    assert miss.status == "expired" and "not reached" in miss.reject_reason
    assert service.available_cash(account) == pytest.approx(account.cash)  # reservation released


def test_settlement_is_idempotent(db_session, user):
    service = _service(Clock(TUE_BEFORE_OPEN))
    account = service.create_account(db_session, user, "Main", 100_000)
    service.place_order(db_session, account, "NABIL", "buy", "market", 10)
    bars = {"NABIL": Bar(close=505.0)}

    service.settle_pending(db_session, TUE, bars)
    cash_after = account.cash
    stats = service.settle_pending(db_session, TUE, bars)

    assert stats["filled"] == 0 and account.cash == cash_after
    assert db_session.query(PaperEquitySnapshot).count() == 1


def test_rejections_are_recorded_with_reasons(db_session, user):
    service = _service(Clock(TUE_OPEN))
    account = service.create_account(db_session, user, "Main", 10_000)

    too_big = service.place_order(db_session, account, "NABIL", "buy", "market", 100)
    short = service.place_order(db_session, account, "NABIL", "sell", "market", 10)
    band = service.place_order(db_session, account, "NABIL", "buy", "limit", 10, limit_price=600.0)
    unknown = service.place_order(db_session, account, "ZZZZ", "buy", "market", 10)

    assert [o.status for o in (too_big, short, band, unknown)] == ["rejected"] * 4
    assert "Not enough cash" in too_big.reject_reason
    assert "short selling" in short.reject_reason
    assert "circuit band" in band.reject_reason
    assert "No price data" in unknown.reject_reason
    assert account.cash == 10_000


def test_pending_sells_reserve_shares(db_session, user):
    clock = Clock(TUE_OPEN)
    service = _service(clock)
    account = service.create_account(db_session, user, "Main", 100_000)
    service.place_order(db_session, account, "NABIL", "buy", "market", 20)

    clock.now = TUE_AFTER_CLOSE
    first = service.place_order(db_session, account, "NABIL", "sell", "market", 15)
    second = service.place_order(db_session, account, "NABIL", "sell", "market", 10)
    assert (first.status, second.status) == ("pending", "rejected")

    service.cancel_order(db_session, first)
    assert service.available_shares(account, "NABIL") == 20


def test_round_trip_summary_and_reset(db_session, user):
    clock = Clock(TUE_OPEN)
    service = _service(clock)
    account = service.create_account(db_session, user, "Main", 100_000)
    service.place_order(db_session, account, "NABIL", "buy", "market", 20)
    service.place_order(db_session, account, "NABIL", "sell", "market", 20)

    summary = service.account_summary(account)
    assert summary["positions"] == []
    assert summary["realized_pnl"] < 0  # same price in and out -> fees are the loss
    assert summary["fees_paid"] == pytest.approx(-summary["realized_pnl"])
    assert summary["equity"] == pytest.approx(100_000 + summary["realized_pnl"])

    board = service.leaderboard(db_session)
    assert board[0]["trader"] == "tr***@example.com" and board[0]["trades"] == 2

    service.reset_account(db_session, account)
    assert account.cash == 100_000 and account.orders == [] and account.positions == []


def test_account_limits(db_session, user):
    service = _service(Clock(TUE_OPEN))
    with pytest.raises(ValueError):
        service.create_account(db_session, user, "Huge", 10**12)
    for i in range(5):
        service.create_account(db_session, user, f"A{i}", 1_000)
    with pytest.raises(ValueError):
        service.create_account(db_session, user, "Sixth", 1_000)
