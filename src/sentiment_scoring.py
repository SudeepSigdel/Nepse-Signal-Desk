"""
Scores scraped news headlines (data/raw/news_headlines.csv, built by
scrapper/news_scraper.py) with a pretrained financial-sentiment model and
aggregates them into a daily MARKET-WIDE sentiment score.

Market-wide, not per-symbol: ShareSansar's category pages return general
market/economic headlines, not company-tagged ones, and NEPSE listings share
a small free float and index-driven behaviour where broad market sentiment
moves most stocks together - a reasonable simplification for a first pass.
Per-symbol sentiment (matching headlines to specific companies) is a
documented future extension, not something faked here.

Model: ProsusAI/finbert - a BERT model fine-tuned specifically on financial
text for 3-class sentiment (positive/negative/neutral), chosen because the
scraped headlines are English-language financial journalism (verified by
inspecting scraped samples), which plain multilingual sentiment models
handle worse than a finance-tuned English model.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
HEADLINES_PATH = RAW_DIR / "news_headlines.csv"
OUTPUT_PATH = PROCESSED_DIR / "market_sentiment.parquet"

MODEL_NAME = "ProsusAI/finbert"
SMOOTHING_HALFLIFE_DAYS = 3  # decay-weighted rolling average window


def score_headlines(titles: list[str]) -> np.ndarray:
    """Return a signed polarity score in [-1, 1] per headline: +score if
    positive, -score if negative, 0 if neutral (confidence-weighted)."""
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
        # neutral stays 0
    return polarity


def main():
    if not HEADLINES_PATH.exists():
        print(f"No headlines file at {HEADLINES_PATH} - run scrapper/news_scraper.py first.")
        return

    headlines = pd.read_csv(HEADLINES_PATH)
    headlines["date"] = pd.to_datetime(headlines["date"], errors="coerce")
    headlines = headlines.dropna(subset=["date", "title"])

    if headlines.empty:
        print("Headlines file has no usable rows.")
        return

    print(f"Loaded {len(headlines):,} headlines spanning "
          f"{headlines['date'].min().date()} -> {headlines['date'].max().date()}")

    print(f"Scoring with {MODEL_NAME} (downloads the model on first run)...")
    headlines["polarity"] = score_headlines(headlines["title"].tolist())

    daily = (
        headlines.groupby(headlines["date"].dt.normalize())
        .agg(n_headlines=("polarity", "size"), Sentiment_score=("polarity", "mean"))
        .reset_index()
        .rename(columns={"date": "Date"})
        .sort_values("Date")
    )

    # Decay-weighted smoothing: today's score blends with recent days so a
    # single noisy/low-count day doesn't swing the feature on its own.
    daily["Sentiment_score_smoothed"] = (
        daily.set_index("Date")["Sentiment_score"]
        .ewm(halflife=f"{SMOOTHING_HALFLIFE_DAYS}D", times=daily["Date"])
        .mean()
        .values
    )

    os.makedirs(PROCESSED_DIR, exist_ok=True)
    daily.to_parquet(OUTPUT_PATH, index=False)

    print(f"\nDaily market sentiment ({len(daily)} days):")
    print(daily.to_string(index=False))
    print(f"\nSaved -> {OUTPUT_PATH}")
    print(
        f"\nNOTE: coverage currently spans only {len(daily)} day(s). This "
        "file only grows going forward as scrapper/news_scraper.py + this "
        "script run daily - there is no historical backfill available from "
        "the source site (see module docstring)."
    )


if __name__ == "__main__":
    main()
