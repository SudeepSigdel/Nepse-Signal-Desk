"""Tests for price-history cleaning (swapped dates, bad prints, corporate actions)."""

import numpy as np
import pandas as pd
import pytest

from app.trading.price_quality import clean_prices, drop_price_spikes, repair_misdated_rows


def series(symbol, rows):
    """rows: list of (date string, close[, volume])."""
    return pd.DataFrame(
        [{"Symbol": symbol, "Date": pd.Timestamp(r[0]), "Close": float(r[1]), "Volume": float(r[2] if len(r) > 2 else 1000)}
         for r in rows]
    )


def test_swapped_duplicate_keeps_the_copy_that_fits():
    # Real session 2026-01-05 (Mon) = 400; parser bug also stored it as 2026-05-01 (Fri).
    df = series("AAA", [
        ("2026-01-04", 398), ("2026-01-05", 400, 777), ("2026-01-06", 402),
        ("2026-04-30", 200), ("2026-05-01", 400, 777), ("2026-05-04", 201),
    ])
    out, stats = repair_misdated_rows(df)
    assert stats["swapped_duplicates_dropped"] == 1
    assert pd.Timestamp("2026-01-05") in set(out["Date"])
    assert pd.Timestamp("2026-05-01") not in set(out["Date"])


def test_off_calendar_row_relocates_when_it_fits_else_drops():
    # 2026-07-04 is a Saturday; swapped 2026-04-07 (Tue) is missing and fits between 100 and 101.
    df = series("AAA", [("2026-04-06", 100), ("2026-04-08", 101), ("2026-07-03", 150), ("2026-07-04", 100.5), ("2026-07-06", 151)])
    out, stats = repair_misdated_rows(df)
    assert stats["off_calendar_relocated"] == 1
    assert out.loc[out["Date"] == pd.Timestamp("2026-04-07"), "Close"].item() == 100.5

    bad = series("BBB", [("2026-04-06", 100), ("2026-04-08", 101), ("2026-08-01", 300)])  # Sat, doesn't fit Jan 8
    out, stats = repair_misdated_rows(bad)
    assert stats["off_calendar_dropped"] == 1 and len(out) == 2


def test_single_spike_removed_but_level_shift_kept():
    spike = series("AAA", [("2026-06-01", 100), ("2026-06-02", 50), ("2026-06-03", 101), ("2026-06-04", 102)])
    out, removed = drop_price_spikes(spike)
    assert removed == 1 and 50 not in out["Close"].tolist()

    bonus = series("BBB", [("2026-06-01", 100), ("2026-06-02", 80), ("2026-06-03", 81), ("2026-06-04", 82)])
    out, removed = drop_price_spikes(bonus)
    assert removed == 0 and len(out) == 4


def test_clean_prices_end_to_end_and_idempotent():
    df = pd.concat([
        series("AAA", [("2026-06-01", 100), ("2026-06-02", 50), ("2026-06-03", 101), ("2026-06-04", 80), ("2026-06-05", 81)]),
        series("BBB", [("2026-06-01", 10), ("2026-06-02", 10.5), ("2026-06-03", 10.2)]),
    ])
    out, report = clean_prices(df)
    assert report["spikes_dropped"] == 1 and report["corporate_action_gaps_adjusted"] == 1
    closes = out[out.Symbol == "AAA"]["Close"].tolist()
    assert closes[-1] == 81 and max(abs(np.diff(np.log(closes)))) < np.log(1.105)
    # Clean data passes through unchanged.
    again, report2 = clean_prices(out)
    assert report2["rows_in"] == report2["rows_out"] and report2["corporate_action_gaps_adjusted"] == 0
    pd.testing.assert_series_equal(again["Close"], out["Close"])
    assert out[out.Symbol == "BBB"]["Close"].tolist() == pytest.approx([10, 10.5, 10.2])


def test_rows_without_date_or_price_are_dropped_not_crashing():
    df = series("AAA", [("2026-06-01", 100), ("2026-06-02", 101)])
    df = pd.concat([df, pd.DataFrame([{"Symbol": "AAA", "Date": pd.NaT, "Close": 99.0, "Volume": 1.0},
                                      {"Symbol": "AAA", "Date": pd.Timestamp("2026-06-03"), "Close": 0.0, "Volume": 1.0}])])
    out, report = clean_prices(df)
    assert report["unusable_rows_dropped"] == 2 and len(out) == 2
