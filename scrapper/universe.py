"""
NEPSE symbol universe: every listed ordinary equity.

Source: stockmap.json published (and auto-refreshed daily) by the
NepseAPI-Unofficial repo, which mirrors NEPSE's security list with sector
info. We keep only ordinary shares - promoter shares, mutual funds / schemes,
debentures and bonds are dropped - and write:

    data/reference/nepse_universe.csv       symbol, company_name, sector, sub_index
    data/reference/symbol_sectors.csv       (existing rows kept, new symbols appended)
    data/reference/symbol_company_names.csv (existing rows kept, new symbols appended)

If the remote stockmap can't be fetched, the last committed
nepse_universe.csv is used, so the daily pipeline never breaks on this step.

Usage:
    python scrapper/universe.py
    python scrapper/universe.py --stockmap path/to/stockmap.json
"""

import argparse
import csv
import json
import logging
import os
import re

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_REFERENCE_DIR = os.path.join(PROJECT_ROOT, "data", "reference")
UNIVERSE_FILENAME = "nepse_universe.csv"
SECTORS_FILENAME = "symbol_sectors.csv"
COMPANY_NAMES_FILENAME = "symbol_company_names.csv"

UNIVERSE_URL_ENV_VAR = "NEPSE_UNIVERSE_URL"
DEFAULT_UNIVERSE_URL = (
    "https://raw.githubusercontent.com/SudeepSigdel/NepseAPI-Unofficial/main/stockmap.json"
)

EXCLUDED_SECTORS = {"Promoter Share", "Mutual Fund"}
# Debentures/bonds and bank-sponsored mutual fund schemes that NEPSE files
# under their sponsor's sector (e.g. "Kumari Equity Fund" under Commercial Banks).
# \byojana\b deliberately does not match "Pariyojana" (= project, e.g. RURU hydro).
NON_EQUITY_NAME_RE = re.compile(r"debenture|bond|rinpatra|%|\bfund\b|\byojana\b", re.IGNORECASE)
# Debenture symbols carry maturity years, e.g. ADBLD83, EBLD86, GBILD86/87.
NON_EQUITY_SYMBOL_RE = re.compile(r"[\d/]")

# Keep sector labels consistent with the hand-maintained symbol_sectors.csv.
SECTOR_LABELS = {
    "Hydro Power": "Hydropower",
    "Non Life Insurance": "Non-Life Insurance",
}
SUB_INDEX_LABELS = {
    "Commercial Banks": "Commercial Bank",
    "Development Banks": "Development Bank",
    "Tradings": "Trading",
}


def is_ordinary_equity(symbol: str, name: str, sector: str) -> bool:
    if sector in EXCLUDED_SECTORS:
        return False
    if NON_EQUITY_SYMBOL_RE.search(symbol):
        return False
    if NON_EQUITY_NAME_RE.search(name or ""):
        return False
    return True


def normalize_sector(sector: str) -> tuple[str, str]:
    """Map a stockmap sector to (sector, sub_index) labels used in this repo."""
    return SECTOR_LABELS.get(sector, sector), SUB_INDEX_LABELS.get(sector, sector)


def build_universe(stockmap: dict) -> list[dict]:
    rows = []
    for symbol, info in stockmap.items():
        symbol = symbol.strip().upper()
        name = (info.get("name") or "").strip()
        raw_sector = (info.get("sector") or "").strip()
        if not symbol or not is_ordinary_equity(symbol, name, raw_sector):
            continue
        sector, sub_index = normalize_sector(raw_sector)
        rows.append({"symbol": symbol, "company_name": name, "sector": sector, "sub_index": sub_index})
    return sorted(rows, key=lambda r: r["symbol"])


def fetch_stockmap(url: str) -> dict | None:
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning("Could not fetch stockmap from %s: %s", url, exc)
        return None
    if not isinstance(data, dict) or not data:
        log.warning("Stockmap from %s is empty or malformed", url)
        return None
    return data


def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: str, fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _merge_reference(path: str, fieldnames: list[str], universe: list[dict]) -> int:
    """Append universe symbols missing from a reference CSV; existing rows win."""
    existing = _read_csv(path)
    known = {row["symbol"].strip().upper() for row in existing if row.get("symbol")}
    added = [row for row in universe if row["symbol"] not in known]
    if added or not os.path.exists(path):
        merged = existing + added
        merged.sort(key=lambda r: r["symbol"].strip().upper())
        _write_csv(path, fieldnames, merged)
    return len(added)


def load_universe_symbols(reference_dir: str = DEFAULT_REFERENCE_DIR) -> list[str]:
    """Symbols from the committed universe file ([] if it doesn't exist yet)."""
    rows = _read_csv(os.path.join(reference_dir, UNIVERSE_FILENAME))
    return sorted({row["symbol"].strip().upper() for row in rows if row.get("symbol")})


def refresh_universe(reference_dir: str, stockmap: dict | None) -> list[dict]:
    universe_path = os.path.join(reference_dir, UNIVERSE_FILENAME)
    if stockmap is None:
        rows = _read_csv(universe_path)
        log.warning("Using last committed universe (%s symbols) from %s", len(rows), universe_path)
        return rows

    rows = build_universe(stockmap)
    if not rows:
        log.warning("Stockmap yielded no equities; keeping existing universe file")
        return _read_csv(universe_path)

    os.makedirs(reference_dir, exist_ok=True)
    _write_csv(universe_path, ["symbol", "company_name", "sector", "sub_index"], rows)
    log.info("Universe: %s ordinary equities (of %s listed securities) -> %s", len(rows), len(stockmap), universe_path)

    added_sectors = _merge_reference(
        os.path.join(reference_dir, SECTORS_FILENAME), ["symbol", "sector", "sub_index"], rows
    )
    added_names = _merge_reference(
        os.path.join(reference_dir, COMPANY_NAMES_FILENAME), ["symbol", "company_name"], rows
    )
    log.info("Reference files: +%s sector rows, +%s company-name rows", added_sectors, added_names)
    return rows


def parse_args():
    parser = argparse.ArgumentParser(description="Refresh the NEPSE ordinary-equity universe.")
    parser.add_argument("--reference-dir", default=DEFAULT_REFERENCE_DIR)
    parser.add_argument(
        "--url",
        default=os.getenv(UNIVERSE_URL_ENV_VAR, DEFAULT_UNIVERSE_URL),
        help=f"stockmap.json URL (defaults to ${UNIVERSE_URL_ENV_VAR} or the NepseAPI-Unofficial repo).",
    )
    parser.add_argument("--stockmap", default="", help="Read stockmap.json from a local path instead of --url.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.stockmap:
        with open(args.stockmap, encoding="utf-8") as f:
            stockmap = json.load(f)
    else:
        stockmap = fetch_stockmap(args.url)
    refresh_universe(args.reference_dir, stockmap)


if __name__ == "__main__":
    main()
