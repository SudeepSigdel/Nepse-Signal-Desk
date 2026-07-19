"""
Scrapes NEPSE-related news headlines from ShareSansar's category pages.

IMPORTANT LIMITATION: ShareSansar's category pages (e.g. /category/latest)
only ever expose their current ~10 most recent headlines each - there is no
working pagination, sitemap, or date-range archive to backfill years of
history from. This means this script's own coverage only grows going
forward, one day of headlines at a time, exactly like nepse_scraper.py
grows price history. Run this daily (via automation/daily_pipeline.py) to
accumulate coverage over time.

Historical coverage instead comes from scrapper/gdelt_scraper.py (a one-off
backfill from GDELT's archive), which writes into the same
data/raw/news_headlines.csv this script does - see that module's docstring.
"""

import argparse
import logging
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from news_common import update_headlines_csv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DEFAULT_DELAY = 1.0
OUTPUT_FILENAME = "news_headlines.csv"

# Categories that between them cover general market/economic news relevant
# to NEPSE-listed companies as a whole (not per-symbol - see sentiment_scoring.py).
DEFAULT_CATEGORIES = [
    "latest", "market", "economy", "capital", "ipo", "corporate", "bank", "feature",
]

URL_DATE_RE = re.compile(r"-(\d{4}-\d{2}-\d{2})$")


def build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    retries = Retry(
        total=3, connect=3, read=3, backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def parse_args():
    parser = argparse.ArgumentParser(description="ShareSansar news headline scraper.")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, help="Directory to write news_headlines.csv.")
    parser.add_argument(
        "--categories", default=",".join(DEFAULT_CATEGORIES),
        help="Comma separated ShareSansar category slugs to scrape.",
    )
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay in seconds between category requests.")
    return parser.parse_args()


def fetch_category_headlines(session, category):
    url = f"https://www.sharesansar.com/category/{category}"
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        log.warning("  [%s] request failed: %s", category, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    rows = []
    for heading in soup.select("h4.featured-news-title"):
        anchor = heading.find_parent("a")
        if not anchor:
            continue
        href = anchor.get("href", "").strip()
        title = heading.get_text(strip=True)
        match = URL_DATE_RE.search(href)
        if not href or not title or not match:
            continue
        rows.append({
            "date": match.group(1),
            "title": title,
            "url": href,
            "category": category,
            "source": "sharesansar",
            "domain": "sharesansar.com",
        })
    return rows


def main():
    args = parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]

    session = build_session()
    all_rows = []

    log.info("=" * 64)
    log.info("ShareSansar News Scraper")
    log.info("Categories: %s", ", ".join(categories))
    log.info("=" * 64)

    for category in categories:
        rows = fetch_category_headlines(session, category)
        log.info("  [%s] %d headlines found", category, len(rows))
        all_rows.extend(rows)
        time.sleep(args.delay)

    combined, added = update_headlines_csv(args.raw_dir, all_rows)
    log.info("=" * 64)
    log.info("Total headlines in archive: %d (added %d new this run)", len(combined), added)
    log.info("Saved -> %s", os.path.join(args.raw_dir, OUTPUT_FILENAME))


if __name__ == "__main__":
    main()
