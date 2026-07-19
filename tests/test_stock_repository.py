"""Tests for stock-history pagination in StockRepository."""

from pathlib import Path

import pandas as pd

from app.repositories.stock_repository import StockRepository


def repository_with_rows(count: int = 10) -> StockRepository:
    repository = StockRepository(Path("unused.parquet"))
    repository.features_df = pd.DataFrame(
        {
            "Symbol": ["AAA"] * count + ["BBB"],
            "Date": pd.date_range("2026-01-01", periods=count).tolist()
            + [pd.Timestamp("2026-01-01")],
            "Close": list(range(count)) + [999],
        }
    )
    repository.all_symbols = ["AAA", "BBB"]
    return repository


def test_latest_page_is_sorted_and_symbol_scoped():
    repository = repository_with_rows()
    page = repository.get_stock_data("AAA", days=3)
    assert page is not None
    assert page["Close"].tolist() == [7, 8, 9]
    assert page["Symbol"].unique().tolist() == ["AAA"]
    assert repository.has_older_data("AAA", days=3, offset=0)


def test_offset_returns_older_page_without_overlap():
    repository = repository_with_rows()
    page = repository.get_stock_data("AAA", days=3, offset=3)
    assert page is not None
    assert page["Close"].tolist() == [4, 5, 6]
    assert repository.has_older_data("AAA", days=3, offset=3)


def test_partial_oldest_page_and_exhaustion():
    repository = repository_with_rows()
    page = repository.get_stock_data("AAA", days=4, offset=8)
    assert page is not None
    assert page["Close"].tolist() == [0, 1]
    assert not repository.has_older_data("AAA", days=4, offset=8)


def test_offset_beyond_history_returns_none():
    repository = repository_with_rows()
    assert repository.get_stock_data("AAA", days=3, offset=20) is None
    assert not repository.has_older_data("MISSING", days=3, offset=0)
