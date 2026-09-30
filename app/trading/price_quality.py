"""
Daily price cleaning shared by the ML pipeline (src/02_data_cleaning.py) and
the agent backtester.

Problems found in the scraped history, and the fix for each, in order:

1. Day/month-swapped rows. Sharesansar dates were parsed with dayfirst=True,
   turning ISO 2026-01-05 into 1 May. That left exact duplicates (same close
   AND volume on a date and on its swapped date) plus rows on days NEPSE
   doesn't trade. Duplicates keep the copy that fits its neighbours; off-
   calendar rows move to their swapped date when they fit there, else drop.
2. Single-row spikes: a move beyond the ±10% circuit that immediately
   reverses is a bad print, not a trade.
3. Bonus / right-share adjustments: a persistent gap beyond the circuit is a
   corporate action in unadjusted data, so earlier prices are back-adjusted.
"""

import numpy as np
import pandas as pd

from app.trading.calendar import is_trading_weekday

CIRCUIT_GAP = 0.105  # a hair above NEPSE's ±10% daily limit
_LOG_GAP = float(np.log1p(CIRCUIT_GAP))
PRICE_COLUMNS = ("Open", "High", "Low", "Close")


def _swap_day_month(dates: pd.Series) -> pd.Series:
    return pd.to_datetime(
        {"year": dates.dt.year, "month": dates.dt.day, "day": dates.dt.month}, errors="coerce"
    )


def _misfit(df: pd.DataFrame) -> pd.Series:
    """How badly each row fits between its neighbours (sum of absolute log moves)."""
    log_close = np.log(df["Close"].where(df["Close"] > 0))
    grouped = log_close.groupby(df["Symbol"])
    move_in = (log_close - grouped.shift(1)).abs().fillna(0)
    move_out = (grouped.shift(-1) - log_close).abs().fillna(0)
    return move_in + move_out


def _trading_day_mask(dates: pd.Series) -> pd.Series:
    unique = pd.Series(pd.unique(dates))
    ok = {d: is_trading_weekday(pd.Timestamp(d).date()) for d in unique}
    return dates.map(ok).astype(bool)


def repair_misdated_rows(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = frame.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    stats = {"swapped_duplicates_dropped": 0, "off_calendar_relocated": 0, "off_calendar_dropped": 0}

    # 1a. Exact duplicates across a day/month swap.
    swappable = (df["Date"].dt.day <= 12) & (df["Date"].dt.day != df["Date"].dt.month)
    candidates = df[swappable].assign(swapped=_swap_day_month(df.loc[swappable, "Date"]))
    twins = candidates.reset_index().merge(
        df.reset_index()[["index", "Symbol", "Date", "Close", "Volume"]],
        left_on=["Symbol", "swapped", "Close", "Volume"],
        right_on=["Symbol", "Date", "Close", "Volume"],
        suffixes=("", "_twin"),
    )
    if not twins.empty:
        misfit = _misfit(df)
        on_calendar = _trading_day_mask(df["Date"])
        drop = set()
        for a, b in zip(twins["index"], twins["index_twin"]):
            if a in drop or b in drop:
                continue
            # An off-calendar copy is always the wrong one; otherwise keep the better fit.
            if on_calendar[a] != on_calendar[b]:
                drop.add(a if not on_calendar[a] else b)
            else:
                drop.add(a if misfit[a] > misfit[b] else b)
        df = df.drop(index=sorted(drop)).reset_index(drop=True)
        stats["swapped_duplicates_dropped"] = len(drop)

    # 1b. Remaining rows on days NEPSE didn't trade.
    off = ~_trading_day_mask(df["Date"])
    if off.any():
        present = set(zip(df["Symbol"], df["Date"]))
        by_symbol = {s: g for s, g in df[~off].groupby("Symbol")}
        relocate, drop = {}, []
        for idx, row in df[off].iterrows():
            target = None
            if row["Date"].day <= 12:
                swapped = pd.Timestamp(year=row["Date"].year, month=row["Date"].day, day=row["Date"].month)
                if is_trading_weekday(swapped.date()) and (row["Symbol"], swapped) not in present:
                    target = swapped
            if target is not None and row["Close"] > 0:
                g = by_symbol.get(row["Symbol"])
                before = g[g["Date"] < target]["Close"].tail(1) if g is not None else pd.Series(dtype=float)
                after = g[g["Date"] > target]["Close"].head(1) if g is not None else pd.Series(dtype=float)
                fits = all(abs(np.log(row["Close"] / p)) <= _LOG_GAP for p in list(before) + list(after) if p > 0)
                if fits:
                    relocate[idx] = target
                    present.add((row["Symbol"], target))
                    continue
            drop.append(idx)
        for idx, target in relocate.items():
            df.at[idx, "Date"] = target
        df = df.drop(index=drop)
        stats["off_calendar_relocated"] = len(relocate)
        stats["off_calendar_dropped"] = len(drop)

    return df.sort_values(["Symbol", "Date"]).reset_index(drop=True), stats


def drop_price_spikes(frame: pd.DataFrame, max_passes: int = 3) -> tuple[pd.DataFrame, int]:
    """Remove single rows that jump beyond the circuit and straight back (bad prints)."""
    df = frame.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    removed = 0
    for _ in range(max_passes):
        log_close = np.log(df["Close"].where(df["Close"] > 0))
        grouped = log_close.groupby(df["Symbol"])
        move_in = log_close - grouped.shift(1)
        move_out = grouped.shift(-1) - log_close
        round_trip = grouped.shift(-1) - grouped.shift(1)
        spike = (
            (move_in.abs() > _LOG_GAP)
            & (move_out.abs() > _LOG_GAP)
            & (np.sign(move_in) != np.sign(move_out))
            & (round_trip.abs() <= _LOG_GAP)
        )
        if not spike.any():
            break
        removed += int(spike.sum())
        df = df[~spike].reset_index(drop=True)
    return df, removed


def adjust_for_corporate_actions(frame: pd.DataFrame, gap: float = CIRCUIT_GAP) -> tuple[pd.DataFrame, int]:
    """
    Back-adjust prices so impossible overnight gaps don't read as crashes or
    windfalls. Each gap's ratio rescales all earlier prices of that symbol
    (volumes inversely), the standard construction of an adjusted series.
    The latest prices are never changed. Returns (frame, gaps adjusted).
    """
    df = frame.sort_values(["Symbol", "Date"]).copy()
    ratio = df["Close"] / df.groupby("Symbol")["Close"].shift(1)
    is_gap = (ratio - 1).abs() > gap
    step = ratio.where(is_gap, 1.0).fillna(1.0)
    # factor for row i = product of gap ratios strictly after i (within the symbol)
    later = step.groupby(df["Symbol"]).transform(lambda s: s[::-1].cumprod()[::-1].shift(-1, fill_value=1.0))
    for column in PRICE_COLUMNS:
        if column in df:
            df[column] = df[column] * later
    if "Volume" in df:
        df["Volume"] = df["Volume"] / later
    return df, int(is_gap.sum())


def clean_prices(frame: pd.DataFrame, adjust: bool = True) -> tuple[pd.DataFrame, dict]:
    """Full cleaning pass; returns the cleaned frame and a report of what changed."""
    rows_in = len(frame)
    df = frame.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    # Unparseable dates and non-positive closes can't be placed or priced.
    valid = df["Date"].notna() & (df["Close"] > 0)
    unusable = int((~valid).sum())
    df = df[valid]
    df, report = repair_misdated_rows(df)
    report["unusable_rows_dropped"] = unusable
    df, report["spikes_dropped"] = drop_price_spikes(df)
    report["corporate_action_gaps_adjusted"] = 0
    if adjust:
        df, report["corporate_action_gaps_adjusted"] = adjust_for_corporate_actions(df)
    report["rows_in"] = rows_in
    report["rows_out"] = len(df)
    return df.reset_index(drop=True), report
