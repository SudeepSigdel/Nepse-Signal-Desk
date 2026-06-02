import argparse
import logging
import os
import re
import time
from datetime import datetime, timedelta

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

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_RAW_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
DEFAULT_PROCESSED_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
DEFAULT_START_DATE = datetime(2020, 1, 1)
DEFAULT_DELAY = 1.0
WARMUP_DAYS = 60
START_DATE_ENV_VAR = "NEPSE_SCRAPER_START_DATE"
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


SESSION = build_session()


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
        "--symbols",
        default="",
        help="Comma separated symbols. If empty, infer from raw-dir CSVs then fallback list.",
    )
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay in seconds per symbol.")
    parser.add_argument(
        "--source",
        choices=["auto", "sharesansar", "merolagani"],
        default="auto",
        help="Data source. 'auto' tries Sharesansar then falls back to Merolagani.",
    )
    parser.add_argument(
        "--skip-parquet",
        action="store_true",
        help="Skip rebuilding all_stocks_combined.parquet.",
    )
    return parser.parse_args()


def resolve_symbols(raw_dir, symbol_arg):
    if symbol_arg.strip():
        return sorted({s.strip().upper() for s in symbol_arg.split(",") if s.strip()})

    if os.path.isdir(raw_dir):
        symbols = sorted(
            {
                filename[:-4].upper()
                for filename in os.listdir(raw_dir)
                if filename.lower().endswith(".csv")
            }
        )
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
        resp = SESSION.get(url, params=params, timeout=30)
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


def fetch_sharesansar(symbol, start_dt, end_dt):
    sharesansar_session = build_sharesansar_session()
    page_url = f"https://www.sharesansar.com/company/{symbol}"

    try:
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
    out["Date"] = pd.to_datetime(df["published_date"], errors="coerce", dayfirst=True)
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
    if source == "sharesansar":
        return fetch_sharesansar(symbol, start_dt, end_dt)

    if source == "merolagani":
        return fetch_merolagani(symbol, start_dt, end_dt)

    # auto mode
    df = fetch_sharesansar(symbol, start_dt, end_dt)
    if df is not None and not df.empty:
        return df
    return fetch_merolagani(symbol, start_dt, end_dt)


def compute_indicators(df):
    df = df.sort_values("Date").copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]

    df["Daily_Return"] = c.pct_change()
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


def update_csv(symbol, new_df, raw_dir):
    csv_path = os.path.join(raw_dir, f"{symbol}.csv")

    if os.path.exists(csv_path):
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


def main():
    args = parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)
    os.makedirs(args.processed_dir, exist_ok=True)

    try:
        global_start = datetime.strptime(args.start_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"--start-date must be in YYYY-MM-DD format (or set {START_DATE_ENV_VAR})")

    today = datetime.today()
    symbols = resolve_symbols(args.raw_dir, args.symbols)

    log.info("=" * 64)
    log.info("NEPSE Scraper (source: %s)", args.source)
    log.info("Global date window: %s -> %s", global_start.date(), today.date())
    log.info("Stocks: %s", len(symbols))
    log.info("=" * 64)

    results = {"updated": [], "current": [], "failed": []}

    for idx, symbol in enumerate(symbols, 1):
        csv_path = os.path.join(args.raw_dir, f"{symbol}.csv")
        last_date = get_last_date(csv_path)

        if last_date is not None:
            # Pull a small warmup window so rolling indicators stay stable.
            symbol_start = max(global_start, last_date.to_pydatetime() - timedelta(days=WARMUP_DAYS))
        else:
            symbol_start = global_start

        log.info("[%3s/%s] %s  (%s -> %s)", idx, len(symbols), symbol, symbol_start.date(), today.date())
        fetched = fetch_data(symbol, symbol_start, today, args.source)

        if fetched is None or fetched.empty:
            log.info("         No data returned")
            results["current"].append(symbol)
            time.sleep(max(0.0, args.delay))
            continue

        try:
            added, latest = update_csv(symbol, fetched, args.raw_dir)
            if added > 0:
                log.info("         +%s rows (latest: %s)", added, latest.date() if pd.notna(latest) else "n/a")
                results["updated"].append((symbol, added))
            else:
                log.info("         Already current")
                results["current"].append(symbol)
        except Exception as exc:
            log.error("         Save failed: %s", exc)
            results["failed"].append(symbol)

        time.sleep(max(0.0, args.delay))

    total_new = sum(count for _, count in results["updated"])
    log.info("\n" + "=" * 64)
    log.info("SUMMARY")
    log.info("=" * 64)
    log.info("Updated : %s stocks (%s new rows)", len(results["updated"]), f"{total_new:,}")
    log.info("Current : %s stocks", len(results["current"]))
    log.info("Failed  : %s -> %s", len(results["failed"]), results["failed"])

    if not args.skip_parquet and results["updated"]:
        log.info("\nRebuilding combined parquet...")
        rebuild_combined_parquet(args.raw_dir, args.processed_dir)
    elif args.skip_parquet:
        log.info("\nSkipped parquet rebuild (--skip-parquet).")
    else:
        log.info("\nAll stocks already current; parquet unchanged.")


if __name__ == "__main__":
    main()