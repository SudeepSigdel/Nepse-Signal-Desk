"""
Backfills historical NEPSE/Nepal-market news headlines from GDELT's DOC 2.0
API and merges them into the same data/raw/news_headlines.csv archive that
scrapper/news_scraper.py (ShareSansar) writes to and src/sentiment_scoring.py
scores. This is a one-off/occasional backfill script, not a daily job -
see news_scraper.py for the script that runs daily going forward.

Why GDELT: ShareSansar's category pages only expose their current ~10
headlines each with no working pagination or archive (see news_scraper.py's
docstring), so that scraper's coverage only grows forward from whenever it
started running. GDELT instead monitors global news in 100+ languages with
a queryable archive back to 2017-01-01 (confirmed against GDELT's own DOC
2.0 API docs: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/),
which lets us backfill years of market-wide sentiment history instead of
waiting for it to accumulate day by day.

Query scope: deliberately narrow ("NEPSE", "Nepal Stock Exchange", "Nepal
share market", "Nepal stock market", English-language sources only) rather
than a bare "Nepal" search, which would flood in unrelated politics/
disaster/tourism coverage. English-only keeps this compatible with the
FinBERT scorer in sentiment_scoring.py without adding a translation step.
Verified live against the API before writing this: a Jan-2024 test window
returned 18 genuinely on-topic NEPSE headlines from thehimalayantimes.com
and myrepublica.nagariknetwork.com.

Rate limit: undocumented in GDELT's own docs, but confirmed live by a 429
response instructing callers to limit requests to one every 5 seconds
("contact kalev.leetaru5@gmail.com for larger queries"). This script sleeps
between every request to respect that; --delay lets you loosen/tighten it.

Pagination: a single query response is capped at 250 articles (GDELT's own
maxrecords limit), so history is fetched in date-chunked windows (monthly
by default). Any window that comes back at the cap is recursively bisected
until each half is under the cap, so no month silently loses articles.
"""

import argparse
import datetime as dt
import logging
import os
import re
import time

import requests
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

GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_MIN_DATE = dt.date(2017, 1, 1)  # earliest date the DOC 2.0 API covers
DEFAULT_QUERY = (
    '("NEPSE" OR "Nepal Stock Exchange" OR "Nepal share market" '
    'OR "Nepal stock market") sourcelang:english'
)
DEFAULT_DELAY = 6.0  # seconds between requests - GDELT enforces ~1 req/5s
MAX_RECORDS = 250  # GDELT's hard per-query cap
MIN_WINDOW_DAYS = 1  # stop bisecting once a window is down to a single day

# GDELT's extracted titles sometimes space out punctuation between digits,
# e.g. "8 . 71 points" - tidy that up before it reaches the sentiment model.
NUMBER_SPACING_RE = re.compile(r"(?<=\d)\s+([.,])\s+(?=\d)")

# GDELT's title extraction falls back to the page's generic <title> tag for
# some outlets/older archived pages instead of the real headline - e.g. every
# old myrepublica.com article in this backfill came back with the literal
# title "My Republica" (221 of 1,483 rows on the first full run). These are
# indistinguishable from genuinely neutral news to the sentiment scorer, so
# drop them rather than let them silently dilute the signal.
GENERIC_TITLE_BLOCKLIST = {"my republica"}


def build_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    retries = Retry(
        total=5, connect=3, read=3, backoff_factor=2.0,
        status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def clean_title(title):
    title = NUMBER_SPACING_RE.sub(r"\1", title)
    return re.sub(r"\s+", " ", title).strip()


def parse_args():
    parser = argparse.ArgumentParser(description="GDELT historical NEPSE news backfill.")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, help="Directory to write news_headlines.csv.")
    parser.add_argument(
        "--start-date", default=GDELT_MIN_DATE.isoformat(),
        help="YYYY-MM-DD to start from (earliest GDELT DOC coverage is 2017-01-01).",
    )
    parser.add_argument("--end-date", default=dt.date.today().isoformat(), help="YYYY-MM-DD to end at (inclusive).")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="GDELT DOC API query string.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Seconds between requests.")
    return parser.parse_args()


def month_windows(start_date, end_date):
    """Yield (window_start, window_end) date pairs, one per calendar month,
    covering [start_date, end_date] inclusive."""
    cur = start_date.replace(day=1)
    while cur <= end_date:
        nxt = dt.date(cur.year + 1, 1, 1) if cur.month == 12 else dt.date(cur.year, cur.month + 1, 1)
        yield max(cur, start_date), min(nxt, end_date + dt.timedelta(days=1))
        cur = nxt


def fetch_window(session, query, delay, window_start, window_end):
    """Fetch articles seen in [window_start, window_end). Recursively bisects
    the window if the MAX_RECORDS cap was hit, since that means the response
    was truncated and articles are being silently dropped."""
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": MAX_RECORDS,
        "sort": "DateAsc",
        "startdatetime": window_start.strftime("%Y%m%d%H%M%S"),
        "enddatetime": window_end.strftime("%Y%m%d%H%M%S"),
    }
    time.sleep(delay)
    try:
        resp = session.get(GDELT_ENDPOINT, params=params, timeout=45)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
    except Exception as exc:
        log.warning("  [%s -> %s] request failed: %s", window_start, window_end, exc)
        return []

    if len(articles) >= MAX_RECORDS and (window_end - window_start).days > MIN_WINDOW_DAYS:
        mid = window_start + (window_end - window_start) / 2
        log.info("  [%s -> %s] hit the %d-record cap - bisecting at %s", window_start, window_end, MAX_RECORDS, mid)
        return (
            fetch_window(session, query, delay, window_start, mid)
            + fetch_window(session, query, delay, mid, window_end)
        )

    return articles


def articles_to_rows(articles):
    rows = []
    for art in articles:
        seendate = art.get("seendate", "")
        url = (art.get("url") or "").strip()
        title = clean_title(art.get("title") or "")
        if not seendate or not url or not title:
            continue
        if title.lower() in GENERIC_TITLE_BLOCKLIST:
            continue
        try:
            date = dt.datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d")
        except ValueError:
            continue
        rows.append({
            "date": date,
            "title": title,
            "url": url,
            "category": "gdelt",
            "source": "gdelt",
            "domain": art.get("domain", ""),
        })
    return rows


def main():
    args = parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)
    start_date = dt.date.fromisoformat(args.start_date)
    end_date = dt.date.fromisoformat(args.end_date)

    if start_date < GDELT_MIN_DATE:
        log.warning("GDELT DOC API coverage starts %s - clamping start date up to it.", GDELT_MIN_DATE)
        start_date = GDELT_MIN_DATE

    session = build_session()
    all_rows = []

    log.info("=" * 64)
    log.info("GDELT News Backfill")
    log.info("Query : %s", args.query)
    log.info("Range : %s -> %s", start_date, end_date)
    log.info("=" * 64)

    for window_start, window_end in month_windows(start_date, end_date):
        window_start_dt = dt.datetime.combine(window_start, dt.time.min)
        window_end_dt = dt.datetime.combine(window_end, dt.time.min)
        articles = fetch_window(session, args.query, args.delay, window_start_dt, window_end_dt)
        rows = articles_to_rows(articles)
        log.info("  [%s -> %s] %d headlines", window_start, window_end, len(rows))
        all_rows.extend(rows)

    combined, added = update_headlines_csv(args.raw_dir, all_rows)
    log.info("=" * 64)
    log.info("Total headlines in archive: %d (added %d new this run)", len(combined), added)
    log.info("Saved -> %s", os.path.join(args.raw_dir, "news_headlines.csv"))


if __name__ == "__main__":
    main()
