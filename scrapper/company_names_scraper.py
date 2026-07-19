"""
Scrapes each NEPSE symbol's full company name from its ShareSansar company
page (e.g. sharesansar.com/company/adbl -> "Agricultural Development Bank
Limited"), building the alias table symbol-level sentiment matching needs
(see src/symbol_sentiment_matching.py) to match news headlines - which
mention company names, not tickers - back to a Symbol.

Output: data/reference/symbol_company_names.csv (symbol, company_name),
following the same data/reference/ convention as symbol_sectors.csv.
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
DEFAULT_REFERENCE_DIR = os.path.join(PROJECT_ROOT, "data", "reference")
DEFAULT_FEATURES_PATH = os.path.join(PROJECT_ROOT, "data", "processed", "all_stocks_features.parquet")
OUTPUT_FILENAME = "symbol_company_names.csv"
DEFAULT_DELAY = 1.5

# "Agricultural Development Bank Limited (\n  ADBL )" -> "Agricultural Development Bank Limited"
NAME_RE = re.compile(r"^(.*?)\s*\(")


def build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    retries = Retry(
        total=3, connect=3, read=3, backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape NEPSE symbol -> company name mapping from ShareSansar.")
    parser.add_argument("--reference-dir", default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--features-path", default=DEFAULT_FEATURES_PATH,
                         help="Parquet file to read the symbol list from.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY)
    return parser.parse_args()


def fetch_company_name(session, symbol):
    url = f"https://www.sharesansar.com/company/{symbol.lower()}"
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("  [%s] request failed: %s", symbol, exc)
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    h1 = soup.find("h1")
    if not h1:
        return None
    match = NAME_RE.search(h1.get_text(" ", strip=True))
    return match.group(1).strip() if match else None


def main():
    args = parse_args()
    os.makedirs(args.reference_dir, exist_ok=True)

    symbols = sorted(pd.read_parquet(args.features_path, columns=["Symbol"])["Symbol"].unique())
    log.info("=" * 64)
    log.info("NEPSE Company Name Scraper (%d symbols)", len(symbols))
    log.info("=" * 64)

    session = build_session()
    rows = []
    for symbol in symbols:
        name = fetch_company_name(session, symbol)
        status = name or "NOT FOUND"
        log.info("  [%s] %s", symbol, status)
        rows.append({"symbol": symbol, "company_name": name})
        time.sleep(args.delay)

    df = pd.DataFrame(rows)
    found = df["company_name"].notna().sum()
    out_path = os.path.join(args.reference_dir, OUTPUT_FILENAME)
    df.to_csv(out_path, index=False)

    log.info("=" * 64)
    log.info("Found %d/%d company names", found, len(symbols))
    log.info("Saved -> %s", out_path)


if __name__ == "__main__":
    main()
