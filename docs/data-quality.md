# Price data quality: what was wrong, what was fixed, and what it changed

## What we found in `all_stocks_features.parquet`

| Problem | Evidence | Cause |
|---|---|---|
| **Day/month-swapped rows** | 1,368 rows in 2026 were exact duplicates (same close *and* volume) of a row on the day/month-swapped date, e.g. AKJCL "2026-04-01 = 190.8" between 395 and 354 | `fetch_sharesansar` parsed ISO dates with `pd.to_datetime(..., dayfirst=True)`, which turns `2026-01-05` into 1 May |
| **Rows on days NEPSE didn't trade** | 152 rows on off-calendar weekdays after the duplicates were removed | Same parser bug, plus a few stray rows |
| **Bad prints** | 32 single rows that jump beyond the ±10% circuit and straight back | Source errors |
| **Unadjusted bonus/right shares** | 513 persistent close-to-close gaps beyond the ±10% circuit (mostly drops) | Stored prices are not adjusted for corporate actions |
| **Trading calendar changed** | Friday rows appear and Sunday rows vanish from April 2026 | NEPSE moved from Sun–Thu to **Mon–Fri** in April 2026 (government two-day weekend). The code still assumed Sun–Thu |

## Fixes

- `app/trading/calendar.py` holds trading weekdays by era: Sun–Thu, a mixed Sun–Fri window in mid-2022, and Mon–Fri from 2026-04-06. It drives paper-trading market hours and the scraper's "already current" check.
- The Sharesansar dates bug is fixed at the source (`parse_sharesansar_dates`). Merolagani, now the primary source, uses timestamps.
- `app/trading/price_quality.clean_prices` runs in `src/02_data_cleaning.py` and in the backtester, in this order:
  1. drop undated or zero-price rows;
  2. drop swapped duplicates, keeping the copy that fits its neighbours;
  3. move off-calendar rows to the swapped date when they fit there, otherwise drop them;
  4. drop single-row spikes;
  5. back-adjust persistent gaps as corporate actions. The latest prices are never changed.

  Technical indicators are then recomputed on the cleaned prices. Counts are written to `data/processed/report/data_quality.json`. `PRICE_REPAIR=0` turns the step off for comparisons.
- `--full-refresh` on the scraper, or the `refetch_prices` workflow input, rebuilds every raw CSV from Merolagani's timestamped history.

After cleaning, 0 rows fall on non-trading days and 0 close-to-close moves exceed the circuit (223,602 of 225,152 rows kept).

## Effect on the model (ablation)

- **Setup:** the same code and raw CSVs, XGBoost, walk-forward folds 1–9, run once with `PRICE_REPAIR=0` and once with `PRICE_REPAIR=1`.
- **No sentiment features:** news sentiment isn't available outside CI, so both runs omit it, and absolute numbers differ from the CI-trained models.
- **Same prices in both backtests:** the agent backtests use the repaired prices in both runs. BuyAndHold is identical in both, so agent differences come only from the model.

**Training labels**

| | Raw | Cleaned |
|---|---|---|
| 10-day forward returns below −20% | 2,884 | 969 |
| BUY / SELL label base rate | 39.7% / 45.6% | 40.3% / 44.7% |

**Fold AUC (out-of-sample)**

| Fold (test year) | BUY raw | BUY clean | SELL raw | SELL clean |
|---|---|---|---|---|
| 1 (2018) | 0.561 | 0.567 | 0.547 | 0.549 |
| 2 (2019) | 0.560 | 0.580 | 0.572 | 0.585 |
| 3 (2020) | 0.476 | 0.482 | 0.495 | 0.498 |
| 4 (2021) | 0.590 | 0.608 | 0.568 | 0.581 |
| 5 (2022) | 0.492 | 0.488 | 0.480 | 0.480 |
| 6 (2023) | 0.526 | 0.533 | 0.513 | 0.516 |
| 7 (2024) | 0.551 | 0.548 | 0.532 | 0.530 |
| 8 (2025) | 0.491 | 0.502 | 0.517 | 0.519 |
| 9 (2026) | 0.468 | 0.461 | 0.545 | 0.533 |
| **Mean** | **0.524** | **0.530** | **0.530** | **0.532** |

**Trading agents: Rs 10 lakh, 2019-02 to 2026-09, all NEPSE costs**

| Agent | Raw-data model | Cleaned-data model |
|---|---|---|
| SignalBot | −13.5% (Sharpe −0.07) | **+9.2% (Sharpe 0.15)** |
| TunedSignalBot | −14.1% (Sharpe −0.11) | **+15.5% (Sharpe 0.20)** |
| CoreSatellite (80/20) | +72.0% (0.44) | +58.9% (0.40) |
| BuyAndHold | +107.5% (0.55) | +107.5% (0.55) |

For the ML-validated strategy in `src/07_backtest.py`, profit factor rose from 1.244 to 1.296 and Sharpe from 0.352 to 0.421.

## Reading this honestly

- Cleaning helps consistently but modestly. BUY AUC improved in 6 of 9 folds, and the model-driven bots went from losing money to making some.
- None of the agent differences is statistically significant (bootstrap CIs include zero).
- Every model strategy still trails simply holding the market. Mean AUC around 0.53 is a weak edge, and NEPSE's round-trip costs of about 1% plus CGT eat most of it at a 10-day horizon.
- Better features and horizons are the next lever, not more cleaning.
