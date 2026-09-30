import argparse
import logging
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from universe import DEFAULT_REFERENCE_DIR, load_universe_symbols  # noqa: E402

from app.trading import calendar as nepse_calendar  # noqa: E402

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DEFAULT_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
DEFAULT_START_DATE = datetime(2020, 1, 1)
# Earliest date requested for symbols with no CSV yet, and for full refetches.
HISTORY_START_DATE = datetime(2012, 1, 1)
DEFAULT_DELAY = 0.0
DEFAULT_WORKERS = 6
DEFAULT_MAX_RPS = 5.0
# Indicators are recomputed over the full merged CSV, so the incremental fetch
# only needs a short overlap to pick up late corrections and detect price
# adjustments (bonus/right shares) against what is already stored.
OVERLAP_DAYS = 10
# Median |relative close difference| on the overlap above which the stored
# history is considered inconsistent with the source and is refetched in full.
ADJUSTMENT_TOLERANCE = 0.01
START_DATE_ENV_VAR = "NEPSE_SCRAPER_START_DATE"
NEPAL_TZ = ZoneInfo("Asia/Kathmandu")
# Sharesansar's endpoint returns empty payloads for large 'length' values.
SHARESANSAR_PAGE_SIZE = 20

FALLBACK_SYMBOLS = [
    "ADBL", "AHL", "AHPC", "AKJCL", "AKPL", "ALICL", "API", "BARUN",
    "BBC", "BEDC", "BFC", "BGWT", "BHPL", "BNL", "BNT", "BPCL", "CBBL",
    "CGH", "CHCL", "CHDC", "CHL", "CIT", "CITY", "CLI", "CZBIL", "DDBL",
    "EBL", "FMDBL", "FOWAD", "GBBL", "GBIME", "GBLBS", "GFCL", "HATHY",
    "HBL", "HDL", "HEI", "HIDCL", "HPPL", "HRL", "ILI", "JBBL", "JFL",
    "JOSHI", "KBL", "KDL", "KPCL", "LICN", "LLBS", "MANDU", "MBL", "MDB",
    "MFIL", "MLBBL", "MNBBL", "MSHL", "NABIL", "NADEP", "NBL", "NHPC",
    "NICA", "NICL", "NIL", "NLG", "NLIC", "NMB", "NRIC", "NTC", "NUBL",
    "OHL", "PCBL", "PRIN", "RAWA", "RBCL", "RHPL", "RLFL", "RNLI", "SADBL",
    "SAHAS", "SANIMA", "SAPDBL", "SBI", "SBL", "SCB", "SHIVM", "SHL",
    "SHPC", "SICL", "SIKLES", "SINDU", "SKBBL", "SNLI", "SPDL", "SWBBL",
    "TRH", "UNHPL", "UNL", "UPCL", "UPPER",
]

COL_ORDER = [
    "Symbol",
    "Date",
    "Open",
    "High",
    "Low",
    "Close",
    "Percent Change",
    "Volume",
    "Turnover",
    "Daily_Return",
    "Log_Return",
    "SMA_5",
    "SMA_20",
    "EMA_12",
    "EMA_26",
    "RSI_14",
    "MACD",
    "MACD_Signal",
    "ATR_14",
    "BB_Middle",
    "BB_Std",
    "BB_Upper",
    "BB_Lower",
    "OBV",
]


def build_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://merolagani.com/",
            "Accept": "application/json, text/plain, */*",
        }
    )
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_thread_local = threading.local()


def get_session():
    """One Merolagani session per worker thread (requests.Session isn't thread-safe)."""
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = build_session()
        _thread_local.session = session
    return session


class RateLimiter:
    """Spaces request starts across all worker threads to at most max_rps per second."""

    def __init__(self, max_rps):
        self.interval = 1.0 / max_rps if max_rps and max_rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self):
        if not self.interval:
            return
        with self._lock:
            now = time.monotonic()
            start_at = max(now, self._next_at)
            self._next_at = start_at + self.interval
        delay = start_at - time.monotonic()
        if delay > 0:
            time.sleep(delay)


RATE_LIMITER = RateLimiter(DEFAULT_MAX_RPS)


def build_sharesansar_session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
        }
    )
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def parse_args():
    parser = argparse.ArgumentParser(description="NEPSE OHLCV scraper.")
    parser.add_argument("--raw-dir", default=DEFAULT_RAW_DIR, help="Directory for per-symbol CSV files.")
    parser.add_argument(
        "--processed-dir",
        default=DEFAULT_PROCESSED_DIR,
        help="Directory for combined parquet output.",
    )
    parser.add_argument(
        "--start-date",
        default=os.getenv(START_DATE_ENV_VAR, DEFAULT_START_DATE.strftime("%Y-%m-%d")),
        help=f"Global minimum fetch date (YYYY-MM-DD). Defaults to ${{{START_DATE_ENV_VAR}}} or {DEFAULT_START_DATE.strftime('%Y-%m-%d')}.",
    )
    parser.add_argument(
        "--history-start",
        default=HISTORY_START_DATE.strftime("%Y-%m-%d"),
        help="Start date for symbols with no CSV yet and for full refetches after a price adjustment.",
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Comma separated symbols. If empty, use the NEPSE universe (data/reference/nepse_universe.csv), "
        "then raw-dir CSVs, then a fallback list.",
    )
    parser.add_argument("--reference-dir", default=DEFAULT_REFERENCE_DIR, help="Directory holding nepse_universe.csv.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Extra delay in seconds after each symbol.")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Symbols fetched concurrently.")
    parser.add_argument(
        "--max-rps",
        type=float,
        default=DEFAULT_MAX_RPS,
        help="Upper bound on HTTP requests per second across all workers (0 = unlimited).",
    )
    parser.add_argument(
        "--source",
        choices=["merolagani-first", "auto", "sharesansar", "merolagani"],
        default="merolagani-first",
        help="Data source. 'merolagani-first' (default) uses Merolagani's single-request chart API and falls "
        "back to Sharesansar; 'auto' tries Sharesansar first.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Fetch every symbol even if its CSV already has the latest trading day.",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Refetch each symbol's whole history from --history-start and replace its CSV "
        "(repairs rows mis-dated by the old Sharesansar date parser).",
    )
    parser.add_argument(
        "--skip-parquet",
        action="store_true",
        help="Skip rebuilding all_stocks_combined.parquet.",
    )
    return parser.parse_args()


def _csv_symbols(raw_dir):
    if not os.path.isdir(raw_dir):
        return set()
    return {filename[:-4].upper() for filename in os.listdir(raw_dir) if filename.lower().endswith(".csv")}


def resolve_symbols(raw_dir, symbol_arg, reference_dir=DEFAULT_REFERENCE_DIR):
    if symbol_arg.strip():
        return sorted({s.strip().upper() for s in symbol_arg.split(",") if s.strip()})

    universe = load_universe_symbols(reference_dir)
    if universe:
        stale = sorted(_csv_symbols(raw_dir) - set(universe))
        if stale:
            # Delisted/merged/suspended: history stays on disk for training, but isn't fetched.
            log.info("Not in current universe (kept, not fetched): %s", ", ".join(stale))
        return universe

    symbols = sorted(_csv_symbols(raw_dir))
    if symbols:
        return symbols

    return FALLBACK_SYMBOLS


def fetch_merolagani(symbol, start_dt, end_dt):
    url = "https://merolagani.com/handlers/TechnicalChartHandler.ashx"
    params = {
        "type": "get_price_history",
        "symbol": symbol,
        "resolution": "D",
        "from": int(start_dt.timestamp()),
        "to": int(end_dt.timestamp()),
    }

    try:
        RATE_LIMITER.wait()
        resp = get_session().get(url, params=params, timeout=30)
        resp.raise_for_status()
        if not resp.text.strip():
            return None
        data = resp.json()
    except Exception as exc:
        log.warning("  [%s] merolagani request failed: %s", symbol, exc)
        return None

    if data.get("s") != "ok" or not data.get("t"):
        return None

    timestamps = data["t"]
    row_count = len(timestamps)
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(timestamps, unit="s", errors="coerce"),
            "Open": pd.to_numeric(data.get("o", [np.nan] * row_count), errors="coerce"),
            "High": pd.to_numeric(data.get("h", [np.nan] * row_count), errors="coerce"),
            "Low": pd.to_numeric(data.get("l", [np.nan] * row_count), errors="coerce"),
            "Close": pd.to_numeric(data.get("c", [np.nan] * row_count), errors="coerce"),
            "Volume": pd.to_numeric(data.get("v", [np.nan] * row_count), errors="coerce"),
        }
    )

    df["Date"] = (df["Date"] + pd.Timedelta(hours=5, minutes=45)).dt.normalize()
    df["Turnover"] = df["Close"] * df["Volume"]
    df["Percent Change"] = df["Close"].pct_change() * 100
    df["Symbol"] = symbol

    df = df.dropna(subset=["Date", "Close"]).copy()
    df = df[df["Close"] > 0].copy()
    return df.sort_values("Date").reset_index(drop=True)


def _parse_sharesansar_token_and_company(html):
    token = None
    meta_tag = re.search(r'<meta[^>]*name=["\']_token["\'][^>]*>', html, re.IGNORECASE)
    if meta_tag:
        content_match = re.search(r'content=["\']([^"\']+)["\']', meta_tag.group(0), re.IGNORECASE)
        if content_match:
            token = content_match.group(1).strip()

    if token is None:
        input_tag = re.search(r'<input[^>]*name=["\']_token["\'][^>]*>', html, re.IGNORECASE)
        if input_tag:
            value_match = re.search(r'value=["\']([^"\']+)["\']', input_tag.group(0), re.IGNORECASE)
            if value_match:
                token = value_match.group(1).strip()

    company_match = re.search(r'<[^>]*id=["\']companyid["\'][^>]*>\s*([^<]+?)\s*</', html, re.IGNORECASE)
    company_id = company_match.group(1).strip() if company_match else None
    return token, company_id


def _safe_to_numeric(series):
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False).str.strip()
    cleaned = cleaned.replace({"": np.nan, "-": np.nan, "--": np.nan, "None": np.nan, "nan": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def parse_sharesansar_dates(values):
    """
    Sharesansar dates may be ISO (2026-01-05) or day-first (05/01/2026).
    pd.to_datetime(..., dayfirst=True) on ISO strings swaps day and month
    (2026-01-05 -> 1 May), which mis-dated thousands of rows in 2026, so ISO
    strings are parsed with an explicit format and only the rest day-first.
    """
    text = pd.Series(values).astype(str).str.strip()
    iso = text.str.match(r"^\d{4}-\d{2}-\d{2}")
    parsed = pd.Series(pd.NaT, index=text.index, dtype="datetime64[ns]")
    parsed[iso] = pd.to_datetime(text[iso].str[:10], format="%Y-%m-%d", errors="coerce")
    parsed[~iso] = pd.to_datetime(text[~iso], errors="coerce", dayfirst=True)
    return parsed


def fetch_sharesansar(symbol, start_dt, end_dt):
    sharesansar_session = build_sharesansar_session()
    page_url = f"https://www.sharesansar.com/company/{symbol}"

    try:
        RATE_LIMITER.wait()
        page_resp = sharesansar_session.get(page_url, timeout=30)
        page_resp.raise_for_status()
    except Exception as exc:
        log.warning("  [%s] sharesansar page request failed: %s", symbol, exc)
        return None

    token, company_id = _parse_sharesansar_token_and_company(page_resp.text)
    if not token or not company_id:
        log.warning("  [%s] sharesansar token/company parse failed", symbol)
        return None

    ajax_url = "https://www.sharesansar.com/company-price-history"
    headers = {
        "X-CSRF-Token": token,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": page_url,
    }

    rows = []
    draw = 1
    start = 0
    total = None

    while True:
        payload = {
            "company": str(company_id),
            "draw": str(draw),
            "start": str(start),
            "length": str(SHARESANSAR_PAGE_SIZE),
        }

        try:
            RATE_LIMITER.wait()
            resp = sharesansar_session.post(ajax_url, data=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            log.warning("  [%s] sharesansar history request failed at start=%s: %s", symbol, start, exc)
            return None

        page_rows = data.get("data", []) if isinstance(data, dict) else []
        if total is None:
            total = int(data.get("recordsTotal", 0) or 0)

        if not page_rows:
            break

        rows.extend(page_rows)
        start += len(page_rows)
        draw += 1
        if total and start >= total:
            break

    if not rows:
        return None

    df = pd.DataFrame(rows)
    if "published_date" not in df.columns:
        return None

    out = pd.DataFrame()
    out["Date"] = parse_sharesansar_dates(df["published_date"]).to_numpy()
    out["Open"] = _safe_to_numeric(df.get("open", pd.Series(dtype="object")))
    out["High"] = _safe_to_numeric(df.get("high", pd.Series(dtype="object")))
    out["Low"] = _safe_to_numeric(df.get("low", pd.Series(dtype="object")))
    out["Close"] = _safe_to_numeric(df.get("close", pd.Series(dtype="object")))
    out["Volume"] = _safe_to_numeric(df.get("traded_quantity", pd.Series(dtype="object")))
    out["Turnover"] = _safe_to_numeric(df.get("traded_amount", pd.Series(dtype="object")))
    out["Percent Change"] = _safe_to_numeric(df.get("per_change", pd.Series(dtype="object")))
    out["Symbol"] = symbol

    out = out.dropna(subset=["Date", "Close"]).copy()
    out["Date"] = out["Date"].dt.normalize()
    out = out[(out["Date"] >= pd.Timestamp(start_dt.date())) & (out["Date"] <= pd.Timestamp(end_dt.date()))].copy()
    out = out[out["Close"] > 0].copy()

    if out["Turnover"].isna().all():
        out["Turnover"] = out["Close"] * out["Volume"]

    return out.sort_values("Date").drop_duplicates(subset=["Date"], keep="last").reset_index(drop=True)


def fetch_data(symbol, start_dt, end_dt, source):
    """Return (df, source_used); df is None when no source returned rows."""
    if source == "sharesansar":
        return fetch_sharesansar(symbol, start_dt, end_dt), "sharesansar"

    if source == "merolagani":
        return fetch_merolagani(symbol, start_dt, end_dt), "merolagani"

    order = ["sharesansar", "merolagani"] if source == "auto" else ["merolagani", "sharesansar"]
    fetchers = {"sharesansar": fetch_sharesansar, "merolagani": fetch_merolagani}
    for name in order:
        df = fetchers[name](symbol, start_dt, end_dt)
        if df is not None and not df.empty:
            return df, name
    return None, None


def nepal_today_end() -> datetime:
    """Return today's Nepal date at end-of-day as a naive datetime for source APIs."""
    nepal_now = datetime.now(NEPAL_TZ)
    return nepal_now.replace(hour=23, minute=59, second=59, microsecond=0, tzinfo=None)


def last_expected_trading_day(nepal_now=None):
    """Most recent session whose close has passed (see app/trading/calendar.py; holidays aren't known)."""
    return pd.Timestamp(nepse_calendar.last_expected_trading_day(nepal_now))


def needs_full_refresh(existing, fetched, tolerance=ADJUSTMENT_TOLERANCE):
    """
    True when fetched closes disagree with stored closes on overlapping dates.

    That happens after a bonus/right adjustment (the source rescales history) or
    when stored history came from a different source. Mixing the two would put
    a fake jump into returns/labels, so the caller refetches full history.
    """
    if existing is None or existing.empty or fetched is None or fetched.empty:
        return False
    left = existing[["Date", "Close"]].copy()
    right = fetched[["Date", "Close"]].copy()
    left["Date"] = pd.to_datetime(left["Date"], errors="coerce").dt.normalize()
    right["Date"] = pd.to_datetime(right["Date"], errors="coerce").dt.normalize()
    overlap = left.merge(right, on="Date", suffixes=("_old", "_new")).dropna()
    overlap = overlap[overlap["Close_old"] > 0]
    if overlap.empty:
        return False
    rel_diff = ((overlap["Close_new"] - overlap["Close_old"]).abs() / overlap["Close_old"]).median()
    return bool(rel_diff > tolerance)


def compute_indicators(df):
    df = df.sort_values("Date").copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    df["Daily_Return"] = c.pct_change()
    # Merolagani doesn't report % change; the first row of each fetch window has none either.
    pct = c.pct_change() * 100
    df["Percent Change"] = df["Percent Change"].fillna(pct) if "Percent Change" in df.columns else pct
    df["Log_Return"] = np.log(c / c.shift(1))
    df["SMA_5"] = c.rolling(5).mean()
    df["SMA_20"] = c.rolling(20).mean()
    df["EMA_12"] = c.ewm(span=12, adjust=False).mean()
    df["EMA_26"] = c.ewm(span=26, adjust=False).mean()
    df["MACD"] = df["EMA_12"] - df["EMA_26"]
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

    delta = c.diff()
    avg_gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = (-delta).clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    df["RSI_14"] = 100 - (100 / (1 + avg_gain / (avg_loss + 1e-9)))

    tr = pd.concat(
        [
            h - l,
            (h - c.shift(1)).abs(),
            (l - c.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["ATR_14"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    df["BB_Middle"] = c.rolling(20).mean()
    df["BB_Std"] = c.rolling(20).std()
    df["BB_Upper"] = df["BB_Middle"] + 2 * df["BB_Std"]
    df["BB_Lower"] = df["BB_Middle"] - 2 * df["BB_Std"]
    df["OBV"] = (v * np.sign(c.diff()).fillna(0)).cumsum()
    return df


def get_last_date(csv_path):
    if not os.path.exists(csv_path):
        return None
    try:
        series = pd.read_csv(csv_path, usecols=["Date"])["Date"]
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.notna().any():
            return parsed.max().normalize()
    except Exception:
        return None
    return None


def load_existing(csv_path):
    if not os.path.exists(csv_path):
        return None
    try:
        existing = pd.read_csv(csv_path)
    except Exception:
        return None
    existing["Date"] = pd.to_datetime(existing["Date"], errors="coerce")
    return existing.dropna(subset=["Date"])


def update_csv(symbol, new_df, raw_dir, replace=False):
    """Merge new rows into {symbol}.csv (or overwrite it when replace=True) and recompute indicators."""
    csv_path = os.path.join(raw_dir, f"{symbol}.csv")

    if replace and os.path.exists(csv_path):
        before_last = load_existing(csv_path)["Date"].max()
        combined = (
            new_df.sort_values("Date")
            .drop_duplicates(subset=["Date"], keep="last")
            .reset_index(drop=True)
        )
        after_last = combined["Date"].max()
        added = int((combined["Date"] > before_last).sum()) if pd.notna(before_last) else len(combined)
    elif os.path.exists(csv_path):
        existing = pd.read_csv(csv_path)
        existing["Date"] = pd.to_datetime(existing["Date"], errors="coerce")
        before_last = existing["Date"].max()
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined["Date"] = pd.to_datetime(combined["Date"], errors="coerce")
        combined = combined.dropna(subset=["Date", "Close"]).copy()
        combined = (
            combined.sort_values("Date")
            .drop_duplicates(subset=["Date"], keep="last")
            .reset_index(drop=True)
        )
        after_last = combined["Date"].max()
        added = int((combined["Date"] > before_last).sum()) if pd.notna(before_last) else len(combined)
    else:
        combined = (
            new_df.sort_values("Date")
            .drop_duplicates(subset=["Date"], keep="last")
            .reset_index(drop=True)
        )
        after_last = combined["Date"].max()
        added = len(combined)

    combined = compute_indicators(combined)
    cols = [col for col in COL_ORDER if col in combined.columns]
    combined[cols].to_csv(csv_path, index=False)
    return added, after_last


def rebuild_combined_parquet(raw_dir, processed_dir):
    dfs = []
    for filename in sorted(os.listdir(raw_dir)):
        if not filename.lower().endswith(".csv"):
            continue
        csv_path = os.path.join(raw_dir, filename)
        tmp = pd.read_csv(csv_path)
        if "Date" not in tmp.columns:
            continue
        tmp["Date"] = pd.to_datetime(tmp["Date"], errors="coerce")
        tmp = tmp.dropna(subset=["Date"]).copy()
        tmp["Symbol"] = filename[:-4].upper()
        dfs.append(tmp)

    if not dfs:
        log.info("No CSV files found to rebuild parquet.")
        return

    combined = pd.concat(dfs, ignore_index=True)
    combined = combined.sort_values(["Symbol", "Date"]).reset_index(drop=True)
    os.makedirs(processed_dir, exist_ok=True)
    out_path = os.path.join(processed_dir, "all_stocks_combined.parquet")
    combined.to_parquet(out_path, index=False)
    log.info("Parquet rebuilt -> %s rows at %s", f"{len(combined):,}", out_path)


def process_symbol(symbol, global_start, history_start, today, last_trading_day, args):
    """Fetch and store one symbol. Returns (status, symbol, rows_added, detail)."""
    csv_path = os.path.join(args.raw_dir, f"{symbol}.csv")
    existing = load_existing(csv_path)
    last_date = existing["Date"].max().normalize() if existing is not None and not existing.empty else None

    full_refresh = getattr(args, "full_refresh", False)
    if last_date is not None and not (args.force or full_refresh) and last_date >= last_trading_day:
        return "current", symbol, 0, "already has latest session"

    if full_refresh:
        fetched, source_used = fetch_data(symbol, history_start, today, args.source)
        if fetched is None or fetched.empty:
            return "failed", symbol, 0, "full refresh returned no data; CSV left unchanged"
        added, latest = update_csv(symbol, fetched, args.raw_dir, replace=True)
        return "refreshed", symbol, added, f"{source_used}, full history rewritten (--full-refresh)"

    if last_date is not None:
        symbol_start = max(global_start, last_date.to_pydatetime() - timedelta(days=OVERLAP_DAYS))
    else:
        symbol_start = history_start

    fetched, source_used = fetch_data(symbol, symbol_start, today, args.source)
    if fetched is None or fetched.empty:
        return "current", symbol, 0, "no data returned"

    replace = False
    if last_date is not None and needs_full_refresh(existing, fetched):
        full_start = min(history_start, existing["Date"].min().to_pydatetime())
        full, full_source = fetch_data(symbol, full_start, today, args.source)
        if full is not None and not full.empty and not needs_full_refresh(full, fetched):
            fetched, source_used, replace = full, full_source, True
        else:
            return "failed", symbol, 0, "price mismatch vs stored history; full refetch unavailable"

    try:
        added, latest = update_csv(symbol, fetched, args.raw_dir, replace=replace)
    except Exception as exc:
        return "failed", symbol, 0, f"save failed: {exc}"
    finally:
        if args.delay:
            time.sleep(args.delay)

    detail = f"{source_used}, latest {latest.date() if pd.notna(latest) else 'n/a'}"
    if replace:
        return "refreshed", symbol, added, detail + ", full history rewritten (price adjustment)"
    if added > 0:
        return "updated", symbol, added, detail
    return "current", symbol, 0, detail


def main():
    args = parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)
    os.makedirs(args.processed_dir, exist_ok=True)

    try:
        global_start = datetime.strptime(args.start_date, "%Y-%m-%d")
        history_start = datetime.strptime(args.history_start, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"--start-date/--history-start must be in YYYY-MM-DD format (or set {START_DATE_ENV_VAR})"
        )

    global RATE_LIMITER
    RATE_LIMITER = RateLimiter(args.max_rps)

    today = nepal_today_end()
    last_trading_day = last_expected_trading_day()
    symbols = resolve_symbols(args.raw_dir, args.symbols, args.reference_dir)
    started = time.monotonic()

    log.info("=" * 64)
    log.info("NEPSE Scraper (source: %s, workers: %s, max rps: %s)", args.source, args.workers, args.max_rps)
    log.info("Global date window: %s -> %s", global_start.date(), today.date())
    log.info("Last expected trading day: %s", last_trading_day.date())
    log.info("Stocks: %s", len(symbols))
    log.info("=" * 64)

    results = {"updated": [], "refreshed": [], "current": [], "failed": []}

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(process_symbol, symbol, global_start, history_start, today, last_trading_day, args): symbol
            for symbol in symbols
        }
        for done, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                status, _, added, detail = future.result()
            except Exception as exc:
                status, added, detail = "failed", 0, f"unexpected error: {exc}"
            if status in ("updated", "refreshed"):
                results[status].append((symbol, added))
                log.info("[%3s/%s] %-8s +%s rows (%s)", done, len(symbols), symbol, added, detail)
            elif status == "failed":
                results["failed"].append(symbol)
                log.warning("[%3s/%s] %-8s FAILED: %s", done, len(symbols), symbol, detail)
            else:
                results["current"].append(symbol)
                log.info("[%3s/%s] %-8s current (%s)", done, len(symbols), symbol, detail)

    changed = results["updated"] + results["refreshed"]
    total_new = sum(count for _, count in changed)
    log.info("\n" + "=" * 64)
    log.info("SUMMARY (%.1fs)", time.monotonic() - started)
    log.info("=" * 64)
    log.info("Updated   : %s stocks (%s new rows)", len(changed), f"{total_new:,}")
    log.info("Refreshed : %s -> %s", len(results["refreshed"]), [s for s, _ in results["refreshed"]])
    log.info("Current   : %s stocks", len(results["current"]))
    log.info("Failed    : %s -> %s", len(results["failed"]), sorted(results["failed"]))

    if not args.skip_parquet and changed:
        log.info("\nRebuilding combined parquet...")
        rebuild_combined_parquet(args.raw_dir, args.processed_dir)
    elif args.skip_parquet:
        log.info("\nSkipped parquet rebuild (--skip-parquet).")
    else:
        log.info("\nAll stocks already current; parquet unchanged.")


if __name__ == "__main__":
    main()
