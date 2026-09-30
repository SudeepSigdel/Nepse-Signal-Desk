"""Tests for the Merolagani-first incremental scraper (no network)."""

import sys
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapper"))

import nepse_scraper as ns  # noqa: E402

NPT = ZoneInfo("Asia/Kathmandu")


def _udf_payload(dates, closes):
    # Merolagani returns bar timestamps at 00:00 NPT, i.e. 18:15 UTC the previous day.
    ts = [int((pd.Timestamp(d) - pd.Timedelta(hours=5, minutes=45)).timestamp()) for d in dates]
    return {"s": "ok", "t": ts, "o": closes, "h": closes, "l": closes, "c": closes, "v": [100] * len(closes)}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = "x" if payload is not None else ""

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return _FakeResponse(self.payload)


def _bars(start, periods, close=100.0):
    dates = pd.bdate_range(start, periods=periods)
    return pd.DataFrame(
        {
            "Symbol": "AAA",
            "Date": dates,
            "Open": close,
            "High": close,
            "Low": close,
            "Close": [close + i for i in range(periods)],
            "Volume": 100.0,
            "Turnover": 100.0 * close,
        }
    )


def _args(tmp_path, **overrides):
    base = dict(raw_dir=str(tmp_path), source="merolagani", force=False, delay=0.0)
    base.update(overrides)
    return Namespace(**base)


def test_fetch_merolagani_parses_udf_payload(monkeypatch):
    session = _FakeSession(_udf_payload(["2026-09-27", "2026-09-28", "2026-09-29"], [100.0, 102.0, 101.0]))
    monkeypatch.setattr(ns, "get_session", lambda: session)

    df = ns.fetch_merolagani("NABIL", datetime(2026, 9, 1), datetime(2026, 9, 30))

    assert list(df["Date"].dt.strftime("%Y-%m-%d")) == ["2026-09-27", "2026-09-28", "2026-09-29"]
    assert list(df["Close"]) == [100.0, 102.0, 101.0]
    assert (df["Symbol"] == "NABIL").all()
    assert len(session.calls) == 1  # whole range in one request


@pytest.mark.parametrize("payload", [None, {"s": "no_data"}, {"s": "ok", "t": []}])
def test_fetch_merolagani_returns_none_without_data(monkeypatch, payload):
    monkeypatch.setattr(ns, "get_session", lambda: _FakeSession(payload))
    assert ns.fetch_merolagani("NABIL", datetime(2026, 9, 1), datetime(2026, 9, 30)) is None


@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2026, 9, 29, 16, 0, tzinfo=NPT), "2026-09-29"),  # Tue after close
        (datetime(2026, 9, 29, 12, 0, tzinfo=NPT), "2026-09-28"),  # Tue before close
        (datetime(2026, 10, 3, 10, 0, tzinfo=NPT), "2026-10-02"),  # Sat -> Fri (Mon-Fri since Apr 2026)
        (datetime(2026, 10, 5, 9, 0, tzinfo=NPT), "2026-10-02"),  # Mon before close -> Fri
        (datetime(2025, 10, 4, 10, 0, tzinfo=NPT), "2025-10-02"),  # 2025 Sat -> Thu (Sun-Thu era)
    ],
)
def test_last_expected_trading_day(now, expected):
    assert ns.last_expected_trading_day(now) == pd.Timestamp(expected)


def test_needs_full_refresh_detects_adjusted_history():
    stored = _bars("2026-09-01", 10, close=200.0)
    same = stored.copy()
    adjusted = stored.assign(Close=stored["Close"] / 1.2)  # 20% bonus share adjustment

    assert not ns.needs_full_refresh(stored, same)
    assert ns.needs_full_refresh(stored, adjusted)
    assert not ns.needs_full_refresh(None, adjusted)


def test_process_symbol_skips_request_when_csv_is_current(tmp_path, monkeypatch):
    ns.update_csv("AAA", _bars("2026-09-01", 21), str(tmp_path))
    last = pd.read_csv(tmp_path / "AAA.csv")["Date"].max()

    def boom(*_args, **_kwargs):
        raise AssertionError("should not fetch")

    monkeypatch.setattr(ns, "fetch_data", boom)
    status, _, added, _ = ns.process_symbol(
        "AAA", datetime(2020, 1, 1), datetime(2012, 1, 1), datetime(2026, 9, 30), pd.Timestamp(last), _args(tmp_path)
    )
    assert (status, added) == ("current", 0)


def test_process_symbol_backfills_new_symbol_from_history_start(tmp_path, monkeypatch):
    requested = []

    def fake_fetch(symbol, start_dt, end_dt, source):
        requested.append(start_dt)
        return _bars("2026-09-01", 21), "merolagani"

    monkeypatch.setattr(ns, "fetch_data", fake_fetch)
    status, _, added, _ = ns.process_symbol(
        "AAA", datetime(2020, 1, 1), datetime(2012, 1, 1), datetime(2026, 9, 30), pd.Timestamp("2026-09-29"),
        _args(tmp_path),
    )
    assert (status, added) == ("updated", 21)
    assert requested == [datetime(2012, 1, 1)]


def test_process_symbol_rewrites_history_after_price_adjustment(tmp_path, monkeypatch):
    stored = _bars("2026-08-03", 30, close=200.0)
    ns.update_csv("AAA", stored, str(tmp_path))
    adjusted_full = pd.concat([stored, _bars("2026-09-14", 1, close=300.0)]).assign(
        Close=lambda d: d["Close"] / 1.2
    )
    calls = []

    def fake_fetch(symbol, start_dt, end_dt, source):
        calls.append(start_dt)
        if len(calls) == 1:  # incremental window
            return adjusted_full[adjusted_full["Date"] >= pd.Timestamp(start_dt)], "merolagani"
        return adjusted_full, "merolagani"

    monkeypatch.setattr(ns, "fetch_data", fake_fetch)
    status, _, _, detail = ns.process_symbol(
        "AAA", datetime(2020, 1, 1), datetime(2012, 1, 1), datetime(2026, 9, 30), pd.Timestamp("2026-09-29"),
        _args(tmp_path),
    )

    assert status == "refreshed"
    assert len(calls) == 2
    saved = pd.read_csv(tmp_path / "AAA.csv")
    assert saved["Close"].iloc[0] == pytest.approx(200.0 / 1.2)
    assert len(saved) == len(adjusted_full)


def test_resolve_symbols_prefers_universe(tmp_path):
    ref = tmp_path / "ref"
    ref.mkdir()
    (ref / "nepse_universe.csv").write_text("symbol,company_name,sector,sub_index\nBBB,B,X,X\nAAA,A,X,X\n")
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "OLD.csv").write_text("Date,Close\n")

    assert ns.resolve_symbols(str(raw), "", str(ref)) == ["AAA", "BBB"]
    assert ns.resolve_symbols(str(raw), "nabil, upper", str(ref)) == ["NABIL", "UPPER"]
    assert ns.resolve_symbols(str(raw), "", str(tmp_path / "missing")) == ["OLD"]


def test_rate_limiter_spaces_requests(monkeypatch):
    clock = {"t": 0.0}
    sleeps = []
    monkeypatch.setattr(ns.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(ns.time, "sleep", lambda s: sleeps.append(s))

    limiter = ns.RateLimiter(max_rps=4)
    for _ in range(3):
        limiter.wait()
    assert sleeps == pytest.approx([0.25, 0.5])


def test_sharesansar_dates_parse_iso_without_day_month_swap():
    parsed = ns.parse_sharesansar_dates(["2026-01-05", "2026-01-05 00:00:00", "05/01/2026", "25/12/2025", "junk"])
    assert list(parsed[:4].dt.strftime("%Y-%m-%d")) == ["2026-01-05", "2026-01-05", "2026-01-05", "2025-12-25"]
    assert pd.isna(parsed.iloc[4])


def test_full_refresh_replaces_history_from_history_start(tmp_path, monkeypatch):
    ns.update_csv("AAA", _bars("2026-09-01", 21), str(tmp_path))
    requested = []

    def fake_fetch(symbol, start_dt, end_dt, source):
        requested.append(start_dt)
        return _bars("2026-08-03", 30, close=50.0), "merolagani"

    monkeypatch.setattr(ns, "fetch_data", fake_fetch)
    status, _, _, detail = ns.process_symbol(
        "AAA", datetime(2020, 1, 1), datetime(2012, 1, 1), datetime(2026, 9, 30), pd.Timestamp("2026-08-01"),
        _args(tmp_path, full_refresh=True),
    )
    assert status == "refreshed" and "--full-refresh" in detail
    assert requested == [datetime(2012, 1, 1)]
    saved = pd.read_csv(tmp_path / "AAA.csv")
    assert len(saved) == 30 and saved["Close"].iloc[0] == 50.0
