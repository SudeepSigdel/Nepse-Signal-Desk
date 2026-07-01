"""
Stock repository: sole owner of feature-data querying (parquet file on disk).

Deliberately unaware of ML feature schemas — callers pass the columns they
need validated (e.g. a model's feature_cols) into get_latest_row.
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.logging_config import get_logger

logger = get_logger(__name__)


class StockRepository:
    """Loads and queries the all-stocks feature parquet file."""

    def __init__(self, features_path: Path):
        self.features_path = features_path
        self.features_df: Optional[pd.DataFrame] = None
        self.all_symbols: List[str] = []

    def load(self) -> None:
        try:
            self.features_df = pd.read_parquet(self.features_path)
            self.features_df["Date"] = pd.to_datetime(self.features_df["Date"])
            self.all_symbols = sorted(self.features_df["Symbol"].unique().tolist())
            logger.info("Loaded %d rows, %d symbols", len(self.features_df), len(self.all_symbols))
        except FileNotFoundError:
            logger.error("Features file not found: %s", self.features_path)
            self.features_df = None
            self.all_symbols = []
        except Exception as e:
            logger.error("Failed to load features: %s", e)
            self.features_df = None
            self.all_symbols = []

    def is_ready(self) -> bool:
        return self.features_df is not None and len(self.all_symbols) > 0

    def get_stock_data(self, symbol: str, days: int = 180) -> Optional[pd.DataFrame]:
        if self.features_df is None:
            return None
        stock_df = (
            self.features_df[self.features_df["Symbol"] == symbol]
            .sort_values("Date")
            .tail(days)
            .copy()
        )
        return stock_df if not stock_df.empty else None

    def get_latest_row(self, symbol: str, required_columns: Optional[List[str]] = None) -> Optional[pd.Series]:
        """Return the most recent row for a symbol, optionally requiring non-null values in required_columns."""
        if self.features_df is None:
            return None

        stock_df = self.features_df[self.features_df["Symbol"] == symbol]
        if required_columns:
            stock_df = stock_df.dropna(subset=required_columns)
        latest = stock_df.sort_values("Date").tail(1)
        return latest.iloc[0] if not latest.empty else None

    def data_version(self) -> Optional[float]:
        """Modification time of the backing parquet file; changes when the daily pipeline refreshes data."""
        try:
            return self.features_path.stat().st_mtime
        except FileNotFoundError:
            return None
