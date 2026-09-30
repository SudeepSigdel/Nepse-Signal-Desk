"""
Stock repository: sole owner of feature-data querying (parquet file on disk).

Deliberately unaware of ML feature schemas — callers pass the columns they
need validated (e.g. a model's feature_cols) into get_latest_row.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.logging_config import get_logger

logger = get_logger(__name__)


class StockRepository:
    """Loads and queries the all-stocks feature parquet file."""

    def __init__(self, features_path: Path):
        self.features_path = features_path
        self.features_df: Optional[pd.DataFrame] = None
        self.all_symbols: List[str] = []
        # symbol -> (start, stop) positions in features_df, which is kept sorted
        # by (Symbol, Date). Lookups become an O(1) iloc slice instead of a
        # boolean scan over every row for every call.
        self._ranges: Dict[str, Tuple[int, int]] = {}

    def load(self) -> None:
        try:
            self.load_frame(pd.read_parquet(self.features_path))
            logger.info("Loaded %d rows, %d symbols", len(self.features_df), len(self.all_symbols))
        except FileNotFoundError:
            logger.error("Features file not found: %s", self.features_path)
            self.features_df = None
            self.all_symbols = []
            self._ranges = {}
        except Exception as e:
            logger.error("Failed to load features: %s", e)
            self.features_df = None
            self.all_symbols = []
            self._ranges = {}

    def load_frame(self, df: pd.DataFrame) -> None:
        """Serve an in-memory frame (used by load(), and by tests/backtests with synthetic data)."""
        df = df.copy()
        df["Date"] = pd.to_datetime(df["Date"])
        self.features_df = df.sort_values(["Symbol", "Date"], kind="mergesort").reset_index(drop=True)
        self._build_index()

    def _build_index(self) -> None:
        symbols = self.features_df["Symbol"].to_numpy()
        starts = [0] + [i for i in range(1, len(symbols)) if symbols[i] != symbols[i - 1]]
        stops = starts[1:] + [len(symbols)]
        self._ranges = {symbols[a]: (a, b) for a, b in zip(starts, stops)}
        self.all_symbols = sorted(self._ranges)

    def _symbol_frame(self, symbol: str) -> Optional[pd.DataFrame]:
        """All rows for a symbol, oldest first (a slice of features_df; don't mutate)."""
        if self.features_df is None:
            return None
        if not self._ranges and len(self.features_df):
            # features_df was assigned directly (e.g. in tests) rather than via load().
            self.features_df = self.features_df.sort_values(["Symbol", "Date"], kind="mergesort").reset_index(drop=True)
            self._build_index()
        bounds = self._ranges.get(symbol)
        if bounds is None:
            return self.features_df.iloc[0:0]
        return self.features_df.iloc[bounds[0]:bounds[1]]

    def is_ready(self) -> bool:
        return self.features_df is not None and len(self.all_symbols) > 0

    def get_stock_data(self, symbol: str, days: int = 180, offset: int = 0) -> Optional[pd.DataFrame]:
        """Return up to `days` rows ending `offset` rows back from the most recent one.

        offset=0 (default) returns the most recent `days` rows, preserving prior
        callers' behavior. offset > 0 lets callers page further back in history.
        """
        symbol_df = self._symbol_frame(symbol)
        if symbol_df is None:
            return None
        end = len(symbol_df) - offset
        start = max(0, end - days)
        stock_df = symbol_df.iloc[start:end].copy()
        return stock_df if not stock_df.empty else None

    def has_older_data(self, symbol: str, days: int, offset: int) -> bool:
        """Whether rows exist further back than the window returned by get_stock_data."""
        symbol_df = self._symbol_frame(symbol)
        if symbol_df is None:
            return False
        return (offset + days) < len(symbol_df)

    def get_latest_row(self, symbol: str, required_columns: Optional[List[str]] = None) -> Optional[pd.Series]:
        """Return the most recent row for a symbol, optionally requiring non-null values in required_columns."""
        stock_df = self._symbol_frame(symbol)
        if stock_df is None or stock_df.empty:
            return None
        if not required_columns:
            return stock_df.iloc[-1]
        # Usually the newest row is complete; only fall back to a scan when it isn't.
        last = stock_df.iloc[-1]
        if not last[required_columns].isna().any():
            return last
        complete = stock_df.dropna(subset=required_columns)
        return complete.iloc[-1] if not complete.empty else None

    def close_change_since(self, symbol: str, start) -> Optional[Tuple[pd.Timestamp, float, float]]:
        """(first date on/after start, its close, latest close) for a symbol, or None."""
        frame = self._symbol_frame(symbol)
        if frame is None or frame.empty:
            return None
        after = frame[(frame["Date"] >= pd.Timestamp(start)) & (frame["Close"] > 0)]
        if after.empty:
            return None
        first, last = after.iloc[0], after.iloc[-1]
        return first["Date"], float(first["Close"]), float(last["Close"])

    def data_version(self) -> Optional[float]:
        """Modification time of the backing parquet file; changes when the daily pipeline refreshes data."""
        try:
            return self.features_path.stat().st_mtime
        except FileNotFoundError:
            return None
