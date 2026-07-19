"""
Pilot scraper for MeroLagani's per-symbol floorsheet (individual trade-level
order flow: buyer broker code, seller broker code, quantity, rate) - see
conversation/PR history for why: broker order flow is a genuinely different
signal from price/volume/news, closer to real order flow than anything else
in this pipeline.

DELIBERATELY SMALL SCOPE: this is a pilot to test whether broker-flow
features carry ANY predictive signal before committing to a full historical
backfill (all ~100 symbols x ~9 years would mean tens of thousands of
paginated ASP.NET postback requests against a live commercial trading-data
site - a much bigger undertaking with real IP-block/ToS risk). This script
only covers a curated list of liquid symbols over a ~2-3 month window.

How it works: MeroLagani's Floorsheet.aspx is an ASP.NET WebForms page.
Filtering by symbol/date is done via a postback (not a simple GET), so each
request must:
  1. GET the page fresh to obtain __VIEWSTATE/__VIEWSTATEGENERATOR/__EVENTVALIDATION
  2. POST back with __EVENTTARGET=...lbtnSearchFloorsheet plus the filter
     fields (symbol autosuggest ID + text, date) to get that day's trades
Symbol -> numeric ID mapping comes from /handlers/AutoSuggestHandler.ashx,
which (despite the "term" parameter) returns the full ~1,600-company list in
one call - fetched once and cached, not per-symbol.
"""

import argparse
import logging
import os
import re
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
OUTPUT_FILENAME = "floorsheet_pilot.csv"
BASE_URL = "https://merolagani.com/Floorsheet.aspx"
AUTOSUGGEST_URL = "https://merolagani.com/handlers/AutoSuggestHandler.ashx"
DEFAULT_DELAY = 1.0

# Curated pilot symbols: the ~12 that had real individual news coverage
# (see src/symbol_sentiment_scoring.py results) plus other large, liquid
# banks/financials, since illiquid small-caps would give near-empty
# floorsheets anyway.
DEFAULT_SYMBOLS = [
    "GBIME", "NICA", "SCB", "NMB", "NABIL", "SHL", "MBL", "NBL", "MNBBL",
    "CLI", "SBI", "SANIMA", "ADBL", "HBL", "EBL", "KBL", "CZBIL", "PCBL",
    "NLIC", "NTC",
]


def build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    retries = Retry(
        total=3, connect=3, read=3, backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_symbol_id_map(session):
    """One call resolves the full company list (~1,600 entries) to numeric
    IDs, despite the 'term' query param - not a per-symbol lookup."""
    resp = session.get(AUTOSUGGEST_URL, params={"type": "Company", "term": "a"}, timeout=20)
    resp.raise_for_status()
    entries = resp.json()
    id_map = {}
    for entry in entries:
        symbol = entry.get("d", "").strip().upper()
        if symbol and symbol not in id_map:
            id_map[symbol] = entry["v"]
    return id_map


def get_hidden(soup, name):
    el = soup.find("input", {"name": name})
    return el.get("value", "") if el else ""


def fetch_floorsheet_page(session, symbol, symbol_id, date_str, page_target=None):
    """One page of a (symbol, date) floorsheet. date_str must be M/D/YYYY
    (the format MeroLagani's date textbox expects)."""
    get_resp = session.get(BASE_URL, timeout=20)
    soup = BeautifulSoup(get_resp.text, "lxml")

    payload = {
        "__EVENTTARGET": page_target or "ctl00$ContentPlaceHolder1$lbtnSearchFloorsheet",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": get_hidden(soup, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": get_hidden(soup, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": get_hidden(soup, "__EVENTVALIDATION"),
        "ctl00$ContentPlaceHolder1$ASCompanyFilter$hdnAutoSuggest": str(symbol_id),
        "ctl00$ContentPlaceHolder1$ASCompanyFilter$txtAutoSuggest": symbol,
        "ctl00$ContentPlaceHolder1$txtFloorsheetDateFilter": date_str,
        "ctl00$ContentPlaceHolder1$txtBuyerBrokerCodeFilter": "",
        "ctl00$ContentPlaceHolder1$txtSellerBrokerCodeFilter": "",
    }
    resp = session.post(BASE_URL, data=payload, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_floorsheet_table(html):
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) != 8:
            continue
        rows.append({
            "transact_no": cells[1],
            "symbol": cells[2],
            "buyer_broker": cells[3],
            "seller_broker": cells[4],
            "quantity": cells[5].replace(",", ""),
            "rate": cells[6].replace(",", ""),
            "amount": cells[7].replace(",", ""),
        })
    return rows


def fetch_symbol_date(session, symbol, symbol_id, date_str):
    """All rows for one (symbol, date), paging if >500 rows (MeroLagani's
    per-page cap) - rare for a single symbol but possible for the most
    liquid names."""
    html = fetch_floorsheet_page(session, symbol, symbol_id, date_str)
    rows = parse_floorsheet_table(html)

    count_match = re.search(r"Showing\s+\d+\s*-\s*\d+\s+of\s+(\d+)\s+records", html)
    total = int(count_match.group(1)) if count_match else len(rows)
    if total > 500:
        log.warning("  [%s %s] %d records - only first 500 captured (pagination not implemented for the pilot)",
                     symbol, date_str, total)
    return rows


def parse_args():
    parser = argparse.ArgumentParser(description="Pilot MeroLagani floorsheet scraper.")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--trading-dates-from", default=None,
                         help="Optional parquet path to read the real trading-date calendar from "
                              "(falls back to every calendar day in range otherwise).")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if args.trading_dates_from:
        cal_df = pd.read_parquet(args.trading_dates_from, columns=["Date"])
        dates = sorted(cal_df[
            (cal_df["Date"] >= args.start_date) & (cal_df["Date"] <= args.end_date)
        ]["Date"].dt.normalize().unique())
    else:
        dates = pd.date_range(args.start_date, args.end_date, freq="B")

    session = build_session()
    log.info("=" * 64)
    log.info("MeroLagani Floorsheet Pilot Scraper")
    log.info("Symbols: %d | Dates: %d | Total requests: ~%d", len(symbols), len(dates), len(symbols) * len(dates))
    log.info("=" * 64)

    log.info("Resolving symbol -> company ID map...")
    id_map = fetch_symbol_id_map(session)
    missing_ids = [s for s in symbols if s not in id_map]
    if missing_ids:
        log.warning("No company ID found for: %s (skipping)", missing_ids)
    symbols = [s for s in symbols if s in id_map]

    all_rows = []
    for symbol in symbols:
        symbol_id = id_map[symbol]
        for date in dates:
            date_str = f"{date.month}/{date.day}/{date.year}"
            try:
                rows = fetch_symbol_date(session, symbol, symbol_id, date_str)
            except Exception as exc:
                log.warning("  [%s %s] request failed: %s", symbol, date_str, exc)
                rows = []
            for row in rows:
                row["date"] = date.strftime("%Y-%m-%d")
            log.info("  [%s %s] %d trades", symbol, date_str, len(rows))
            all_rows.extend(rows)
            time.sleep(args.delay)

    df = pd.DataFrame(all_rows)
    out_path = os.path.join(args.raw_dir, OUTPUT_FILENAME)
    df.to_csv(out_path, index=False)
    log.info("=" * 64)
    log.info("Total trades captured: %d", len(df))
    log.info("Saved -> %s", out_path)


if __name__ == "__main__":
    main()
