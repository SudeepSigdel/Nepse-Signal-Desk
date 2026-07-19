"""
Matches scraped news headlines (data/raw/news_headlines.csv) to specific
NEPSE symbols via company-name aliases (data/reference/symbol_company_names.csv,
built by scrapper/company_names_scraper.py), then scores matched headlines
with FinBERT and aggregates to daily PER-SYMBOL sentiment - unlike
sentiment_scoring.py's market-wide (same value for every stock on a day)
aggregate.

Matching approach: each company's "short name" (its legal name with trailing
corporate-form words like Limited/Company/Ltd stripped) must appear as a
whole phrase in the headline title, case-insensitive. Every one of the 100
NEPSE symbols currently listed has a short name of 2+ words after stripping
(verified - see scrapper/company_names_scraper.py output), which keeps
false-positive risk low: matching "Best Finance" as a phrase is far safer
than matching the word "Best" alone. A headline can match more than one
symbol (rare - e.g. two companies sharing a near-identical name).

Coverage is expected to be thin: most of NEPSE's ~100 listed companies get
near-zero individual English-language news coverage (see conversation
history / docs) - this script's job is to measure exactly how thin before
deciding whether to wire per-symbol sentiment into the training pipeline.
"""

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
HEADLINES_PATH = RAW_DIR / "news_headlines.csv"
COMPANY_NAMES_PATH = REFERENCE_DIR / "symbol_company_names.csv"
OUTPUT_PATH = PROCESSED_DIR / "symbol_sentiment.parquet"

MODEL_NAME = "ProsusAI/finbert"
SMOOTHING_HALFLIFE_DAYS = 3

SUFFIX_WORDS = {"limited", "ltd", "company", "co", "public", "pvt"}


def short_name(company_name: str) -> str:
    tokens = company_name.split()
    while tokens and tokens[-1].lower().strip(".") in SUFFIX_WORDS:
        tokens.pop()
    return " ".join(tokens)


def build_alias_patterns(names_df: pd.DataFrame) -> list[tuple[str, re.Pattern]]:
    patterns = []
    for _, row in names_df.iterrows():
        alias = short_name(row["company_name"])
        if len(alias.split()) < 2:
            continue  # skip anything that stripped down to a single word - too risky to match
        pattern = re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE)
        patterns.append((row["symbol"], pattern))
    return patterns


def match_headlines_to_symbols(headlines: pd.DataFrame, patterns: list[tuple[str, re.Pattern]]) -> pd.DataFrame:
    """Returns a long-format frame: one row per (headline, matched symbol)."""
    matches = []
    for idx, title in headlines["title"].items():
        for symbol, pattern in patterns:
            if pattern.search(title):
                matches.append({"headline_idx": idx, "symbol": symbol})
    if not matches:
        return pd.DataFrame(columns=["headline_idx", "symbol"])
    return pd.DataFrame(matches)


def score_headlines(titles: list[str]) -> np.ndarray:
    """Same scoring logic as sentiment_scoring.py - signed polarity in [-1, 1]."""
    from transformers import pipeline

    classifier = pipeline("sentiment-analysis", model=MODEL_NAME, truncation=True)
    results = classifier(titles, batch_size=16)

    polarity = np.zeros(len(titles))
    for i, result in enumerate(results):
        label = result["label"].lower()
        score = result["score"]
        if label == "positive":
            polarity[i] = score
        elif label == "negative":
            polarity[i] = -score
    return polarity


def main():
    if not HEADLINES_PATH.exists():
        print(f"No headlines file at {HEADLINES_PATH} - run scrapper/news_scraper.py / gdelt_scraper.py first.")
        return
    if not COMPANY_NAMES_PATH.exists():
        print(f"No company names file at {COMPANY_NAMES_PATH} - run scrapper/company_names_scraper.py first.")
        return

    headlines = pd.read_csv(HEADLINES_PATH)
    headlines["date"] = pd.to_datetime(headlines["date"], errors="coerce")
    headlines = headlines.dropna(subset=["date", "title"]).reset_index(drop=True)

    names_df = pd.read_csv(COMPANY_NAMES_PATH).dropna(subset=["company_name"])
    patterns = build_alias_patterns(names_df)
    print(f"Built {len(patterns)} matchable company aliases (of {len(names_df)} symbols)")

    matches = match_headlines_to_symbols(headlines, patterns)
    n_matched_headlines = matches["headline_idx"].nunique()
    n_matched_symbols = matches["symbol"].nunique()
    print(f"\nMatched {len(matches):,} (headline, symbol) pairs")
    print(f"  {n_matched_headlines:,} / {len(headlines):,} headlines matched at least one symbol "
          f"({n_matched_headlines / len(headlines) * 100:.1f}%)")
    print(f"  {n_matched_symbols} / {len(names_df)} symbols matched at least one headline")

    if matches.empty:
        print("\nNo symbol matches found - nothing to score. Exiting.")
        return

    print("\nHeadlines matched per symbol:")
    print(matches["symbol"].value_counts().to_string())

    matched_headlines = headlines.loc[matches["headline_idx"].unique()].copy()
    print(f"\nScoring {len(matched_headlines):,} matched headlines with {MODEL_NAME}...")
    matched_headlines["polarity"] = score_headlines(matched_headlines["title"].tolist())

    long_df = matches.merge(
        matched_headlines[["date", "polarity"]], left_on="headline_idx", right_index=True, how="left"
    )

    daily_symbol = (
        long_df.groupby(["symbol", long_df["date"].dt.normalize()])
        .agg(n_headlines=("polarity", "size"), Symbol_sentiment_score=("polarity", "mean"))
        .reset_index()
        .rename(columns={"date": "Date"})
        .sort_values(["symbol", "Date"])
    )

    smoothed = []
    for symbol, group in daily_symbol.groupby("symbol"):
        group = group.set_index("Date").sort_index()
        group["Symbol_sentiment_smoothed"] = (
            group["Symbol_sentiment_score"].ewm(halflife=f"{SMOOTHING_HALFLIFE_DAYS}D", times=group.index).mean()
        )
        smoothed.append(group.reset_index())
    daily_symbol = pd.concat(smoothed, ignore_index=True)

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    daily_symbol.to_parquet(OUTPUT_PATH, index=False)

    print(f"\nSaved -> {OUTPUT_PATH} ({len(daily_symbol):,} symbol-days)")
    print(
        "\nNOTE: coverage is inherently thin - most rows in the main feature "
        "table will have no symbol-level match and should fall back to "
        "market-wide sentiment (see 03_feature_engineering.py)."
    )


if __name__ == "__main__":
    main()
