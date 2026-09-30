"""Tests for the NEPSE ordinary-equity universe builder."""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scrapper"))

import universe  # noqa: E402

STOCKMAP = {
    "NABIL": {"name": "Nabil Bank Limited", "sector": "Commercial Banks"},
    "UPPER": {"name": "Upper Tamakoshi Hydropower Ltd", "sector": "Hydro Power"},
    "RURU": {"name": "Ru Ru Jalbidhyut Pariyojana Limited", "sector": "Hydro Power"},
    "SICL": {"name": "Shikhar Insurance Co. Ltd.", "sector": "Non Life Insurance"},
    "NABILP": {"name": "Nabil Bank Limited Promoter Share", "sector": "Promoter Share"},
    "NIBSF2": {"name": "NIBL Sahabhagita Fund 2", "sector": "Mutual Fund"},
    "ADBLD83": {"name": "ADBL Debenture 2083", "sector": "Commercial Banks"},
    "GBILD86/87": {"name": "Global IME Bank Debenture", "sector": "Commercial Banks"},
    "EBLEB": {"name": "10% Everest Bank Debenture", "sector": "Commercial Banks"},
    "KEF": {"name": "Kumari Equity Fund", "sector": "Commercial Banks"},
    "KSY": {"name": "Kumari Sabal Yojana", "sector": "Commercial Banks"},
}


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_build_universe_keeps_only_ordinary_equity():
    rows = universe.build_universe(STOCKMAP)
    assert [r["symbol"] for r in rows] == ["NABIL", "RURU", "SICL", "UPPER"]


def test_sector_labels_match_existing_reference_file():
    by_symbol = {r["symbol"]: r for r in universe.build_universe(STOCKMAP)}
    assert (by_symbol["UPPER"]["sector"], by_symbol["UPPER"]["sub_index"]) == ("Hydropower", "Hydro Power")
    assert (by_symbol["SICL"]["sector"], by_symbol["SICL"]["sub_index"]) == ("Non-Life Insurance", "Non Life Insurance")
    assert (by_symbol["NABIL"]["sector"], by_symbol["NABIL"]["sub_index"]) == ("Commercial Banks", "Commercial Bank")


def test_refresh_appends_new_symbols_and_keeps_existing_rows(tmp_path):
    sectors = tmp_path / "symbol_sectors.csv"
    sectors.write_text("symbol,sector,sub_index\nNABIL,Hand Curated,Custom\n", encoding="utf-8")

    universe.refresh_universe(str(tmp_path), STOCKMAP)

    rows = {r["symbol"]: r for r in _read(sectors)}
    assert rows["NABIL"]["sector"] == "Hand Curated"
    assert set(rows) == {"NABIL", "RURU", "SICL", "UPPER"}
    assert universe.load_universe_symbols(str(tmp_path)) == ["NABIL", "RURU", "SICL", "UPPER"]
    names = {r["symbol"]: r["company_name"] for r in _read(tmp_path / "symbol_company_names.csv")}
    assert names["UPPER"] == "Upper Tamakoshi Hydropower Ltd"
    assert "\r\n" not in sectors.read_bytes().decode()


def test_refresh_falls_back_to_committed_universe_when_fetch_fails(tmp_path):
    universe.refresh_universe(str(tmp_path), STOCKMAP)
    rows = universe.refresh_universe(str(tmp_path), None)
    assert [r["symbol"] for r in rows] == ["NABIL", "RURU", "SICL", "UPPER"]
