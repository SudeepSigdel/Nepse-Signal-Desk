# Automation — Daily Pipeline

Scripts for orchestrating the NEPSE data pipeline locally and in CI.

---

## Files

| File | Purpose |
|---|---|
| `daily_pipeline.py` | Main orchestrator — runs all pipeline steps in sequence |
| `run_daily_pipeline.sh` | Shell wrapper for Render/cron invocation |
| `SERVER_AUTOMATION_GUIDE.md` | *(replaced by this file)* |

---

## Running Locally

### Full pipeline (scrape + train + backtest + report)

```bash
python automation/daily_pipeline.py
```

Override the scraper's global start date when needed:

```bash
python automation/daily_pipeline.py --start-date 2020-01-01
```

### Skip scraping (use existing raw data)

```bash
python automation/daily_pipeline.py --skip-scrape
```

### Individual pipeline steps

Run scripts from the `src/` directory in order:

```bash
cd src
python 01_data_audit.py
python 02_data_cleaning.py
python 03_feature_engineering.py
python 03b_fix_infinities.py
python 04_label_construction.py
python 05_walk_forward_setup.py
python 06_train_model.py          # BUY classifier (9 rolling annual folds)
python 06b_train_sell_model.py    # SELL classifier (9 rolling annual folds)
python 07_backtest.py
python 08_reporting.py
```

Set `MODEL_FAMILY=random_forest` before these commands if you want the pipeline to train and evaluate Random Forest instead of XGBoost.

Training (`06` and `06b`) is the slow step — expect 10–30 minutes depending on dataset size.

---

## What Each Step Produces

| Script | Output |
|---|---|
| `01_data_audit.py` | Console report of raw data quality |
| `02_data_cleaning.py` | `data/processed/all_stocks_clean.parquet` |
| `03_feature_engineering.py` | `data/processed/all_stocks_features.parquet` |
| `03b_fix_infinities.py` | In-place infinity/NaN cleanup |
| `04_label_construction.py` | `data/processed/all_stocks_labeled.parquet` + `outputs/label_distribution.png` |
| `05_walk_forward_setup.py` | `data/processed/fold_config.json` |
| `06_train_model.py` | `data/processed/models/model_fold{1-9}.pkl` (+ `model_latest.pkl`) or `_rf` suffix + `fold_metrics*.csv` |
| `06b_train_sell_model.py` | `data/processed/models/model_fold{1-9}_sell.pkl` (+ `model_latest_sell.pkl`) or `_rf_sell` suffix + metrics |
| `07_backtest.py` | `outputs/strategy_metrics*.csv` |
| `08_reporting.py` | `outputs/*.png` charts and summary tables |

---

## GitHub Actions Schedule

Three workflows handle CI automation:

### `daily-pipeline.yml` — validates every push/PR, runs the pipeline at 12:15 UTC (6:00 PM Nepal)

1. `validate-frontend` job: type-checks and builds the frontend on every push/PR
2. `run-pipeline` job: checks out repo with write token, installs `requirements.txt`, validates Python code with `compileall` and `pytest`
3. On schedule/manual dispatch/push to `main`: runs `automation/daily_pipeline.py` for the full scrape + train + backtest + reporting flow
4. Commits updated data files back to the repo
5. Uploads pipeline outputs as GitHub artifacts

This keeps the scheduled run aligned with the codebase, including the BUY and SELL model branches.

**Manual trigger:** Actions → Daily Pipeline → Run workflow

### `deploy.yml` — runs on push to `main`

Runs the backend test suite, then (if it passes) builds and pushes the Docker image to `ghcr.io/sudeepsigdel/fyp:latest`. The production Azure VM pulls this image via `docker-compose.prod.yml`.

### `keep-alive.yml` — runs every Monday at 06:00 UTC

Only creates a commit if the last real commit was more than 50 days ago. Prevents GitHub from disabling scheduled workflows on inactive repos.

---

## Scraper

The scraper (`scrapper/nepse_scraper.py`) fetches daily OHLCV data from:
1. **Sharesansar** — primary source
2. **Merolagani** — fallback if Sharesansar is unavailable

Features:
- Incremental updates (only fetches missing dates)
- Retry logic with exponential backoff
- Rebuilds the combined parquet file after each run
- Global start date can be set with `--start-date` or `NEPSE_SCRAPER_START_DATE`
- Per-symbol logs may start later than the global start because the scraper rewinds each symbol by a warmup window when existing CSVs already have data

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Pipeline fails on scrape step | Run with `--skip-scrape` to use existing data |
| `ModuleNotFoundError: utils` | Run scripts from the `src/` directory, not the repo root |
| Model `.pkl` files missing after training | Check `data/processed/models/` exists and disk has space |
| GitHub Actions workflow not triggering | Check Actions tab — if disabled, re-enable and trigger manually |
| Keep-alive creating unexpected commits | Normal if repo has been inactive >50 days |
