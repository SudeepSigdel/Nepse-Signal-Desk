"""
Shared helpers for merging scraped news headlines into the single
data/raw/news_headlines.csv archive that src/sentiment_scoring.py reads from.

Used by both scrapper/news_scraper.py (ShareSansar, daily/forward-only) and
scrapper/gdelt_scraper.py (GDELT, historical backfill) so the two scrapers
don't duplicate merge/dedupe logic and both write into the same schema.
"""

import os

import pandas as pd

OUTPUT_FILENAME = "news_headlines.csv"


def update_headlines_csv(raw_dir, new_rows):
    """Merge new_rows into news_headlines.csv, de-duplicated by url.

    Returns (combined_dataframe, count_of_rows_added).
    """
    csv_path = os.path.join(raw_dir, OUTPUT_FILENAME)
    new_df = pd.DataFrame(new_rows)
    existed_before = os.path.exists(csv_path)

    if existed_before:
        existing = pd.read_csv(csv_path)
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    if combined.empty:
        return combined, 0

    before = len(combined)
    combined = combined.drop_duplicates(subset=["url"], keep="last")
    combined["date"] = pd.to_datetime(combined["date"], errors="coerce")
    combined = combined.dropna(subset=["date", "title"])
    combined = combined.sort_values(["date", "category"]).reset_index(drop=True)
    added = len(combined) - (before - len(new_df)) if existed_before else len(combined)

    combined_out = combined.copy()
    combined_out["date"] = combined_out["date"].dt.strftime("%Y-%m-%d")
    combined_out.to_csv(csv_path, index=False)
    return combined_out, max(added, 0)
