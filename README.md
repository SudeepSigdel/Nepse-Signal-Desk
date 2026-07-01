# NEPSE Signal Desk

An AI-powered stock signal platform for the Nepal Stock Exchange (NEPSE). Scrapes daily market data, trains XGBoost/Random Forest classifiers using walk-forward validation, and exposes a FastAPI backend + React dashboard with BUY / MODERATE / SELL / WEAK_SELL / HOLD signals, interactive candlestick charts, sector/market views, a live model-trust page with real backtest metrics, and persisted user accounts (watchlist + portfolio).

![Python](https://img.shields.io/badge/python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green) ![React](https://img.shields.io/badge/React-18-61dafb) ![XGBoost](https://img.shields.io/badge/XGBoost-3.2-orange) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## How It Works

```
Daily scrape (Sharesansar / Merolagani)
    ↓
Data audit → cleaning → feature engineering → label construction
    ↓
Walk-forward training (9 rolling annual folds, XGBoost or Random Forest) — BUY model + SELL model
    ↓
Backtest → reporting (fold metrics, calibration, threshold sensitivity, strategy comparison)
    ↓
FastAPI serves signals, model performance, accounts, watchlist, portfolio  →  React dashboard
```

The system uses two separate classifiers, selected with `MODEL_FAMILY`:
- **BUY model** — P(stock goes up >1% in 10 days)
- **SELL model** — P(stock goes down >1% in 10 days)

Set `MODEL_FAMILY=xgboost` or `MODEL_FAMILY=random_forest` (default) to choose which trained artifacts the API serves.

Combined, they produce a 5-level verdict: **BUY → MODERATE → HOLD → WEAK_SELL → SELL**

---

## Features

- **Signals**: model-ranked stock table, per-stock BUY/SELL confidence, verdict, active technical signals
- **Interactive charts**: candlestick + SMA/Bollinger + volume + RSI + MACD, synced crosshair (TradingView `lightweight-charts`)
- **Markets**: movers (gainers/losers/turnover/activity) and sector aggregates
- **Model Trust**: real walk-forward AUC per fold, a calibration chart (does stated confidence match the realized outcome rate?), and ML-validated vs. baseline strategy comparison — computed live from backtest artifacts, not hardcoded
- **Accounts**: email/password or Google OAuth signup/login (JWT), with a persisted per-user watchlist and portfolio (Postgres) that survive across devices
- **Exit discipline**: time-based / stop-loss / signal-decay exit guidance for tracked positions

---

## Quick Start

### Backend

```bash
# 1. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate         # Windows
source venv/bin/activate      # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment
cp .env.example .env
# At minimum set DATABASE_URL (a free Neon/Supabase Postgres instance) for
# accounts/watchlist/portfolio to work — everything else has safe defaults.

# 4. Apply database migrations (only needed if DATABASE_URL is set)
alembic upgrade head

# 5. Start the API
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Docker (backend only; see docker-compose.yml)

```bash
docker-compose up
# Backend on :8000. Reads DATABASE_URL/SECRET_KEY/etc. from .env via env_file.
```

---

## Project Structure

```
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point (lifespan, CORS, rate limiting, routers)
│   ├── config.py                 # Pydantic settings (env-driven)
│   ├── constants.py              # Confidence thresholds (single source of truth)
│   ├── schemas.py                # Request / response Pydantic models
│   ├── db.py / db_models.py      # SQLAlchemy engine + User/WatchlistItem/Holding models
│   ├── rate_limit.py             # Shared slowapi limiter (auth brute-force protection)
│   ├── api/routes/                # stocks, signals, positions, performance, auth, watchlist, holdings
│   ├── repositories/              # model/stock/sector/evaluation data access
│   └── services/                  # signal_service, exit_rules, auth_service
│
├── alembic/                      # DB migrations (schema is migration-owned, not auto-created)
│
├── src/                           # ML pipeline (run in order)
│   ├── 01_data_audit.py
│   ├── 02_data_cleaning.py
│   ├── 03_feature_engineering.py
│   ├── 03b_fix_infinities.py
│   ├── 04_label_construction.py
│   ├── 05_walk_forward_setup.py
│   ├── 06_train_model.py         # BUY classifier
│   ├── 06b_train_sell_model.py   # SELL classifier
│   ├── 07_backtest.py
│   ├── 08_reporting.py
│   └── utils.py
│
├── frontend/                      # React + TypeScript dashboard (Vite)
│   └── src/
│       ├── pages/                 # Dashboard, Markets, Watchlist, Portfolio, Trust, Login/Signup, stock detail
│       ├── components/            # dashboard/, stock/, markets/, layout/, auth/, ui/
│       ├── context/                # AuthContext, UserDataContext, StocksContext
│       └── hooks/                  # useStocks, useSignal, useModelPerformance, useWatchlist, usePositions, …
│
├── scrapper/                      # NEPSE data scraper (Sharesansar + Merolagani)
├── automation/                    # Pipeline orchestration scripts
├── data/
│   ├── raw/                       # Scraped CSVs
│   ├── processed/                 # Parquet files, trained models, fold metrics, report artifacts
│   └── reference/                 # Static reference data (e.g. symbol → sector mapping)
├── outputs/                       # Strategy comparison charts/CSVs
├── tests/                         # pytest suite
├── .github/workflows/             # daily-pipeline.yml, deploy.yml, keep-alive.yml
├── Dockerfile                     # Backend image
├── docker-compose.yml             # Local dev stack
└── docker-compose.prod.yml        # Azure VM production stack
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/stocks` | All stocks with signals, ranked by confidence |
| `GET` | `/api/stocks/{symbol}` | OHLCV candles + indicators (RSI, MACD, BB) |
| `GET` | `/api/signal/{symbol}` | BUY + SELL confidence, verdict, description |
| `GET` | `/api/signal/{symbol}/both` | Signal payloads for both model families |
| `GET` | `/api/summary` | Top signals summary |
| `GET` | `/api/model-performance` | Fold AUC, calibration, threshold sensitivity, strategy comparison |
| `POST` | `/api/positions/exit-check` | Exit guidance for a held position |
| `POST` | `/api/auth/signup` / `/api/auth/login` | Email/password auth → JWT |
| `GET` | `/api/auth/me` | Current authenticated user |
| `GET` | `/api/auth/google/login` / `/api/auth/google/callback` | Google OAuth flow |
| `GET`/`POST`/`DELETE` | `/api/watchlist`, `/api/watchlist/{symbol}` | Persisted per-user watchlist |
| `GET`/`POST`/`DELETE` | `/api/holdings`, `/api/holdings/{id}` | Persisted per-user portfolio |

---

## Signal Thresholds

Defined in [`app/constants.py`](app/constants.py) — single source of truth used by the backend and frontend.

| buy_confidence | sell_confidence | Verdict |
|---|---|---|
| ≥ 0.65 | — | 🟢 **BUY** |
| ≥ 0.55 | — | 🟠 **MODERATE** |
| — | ≥ 0.65 | 🔴 **SELL** |
| — | ≥ 0.55 | 🟡 **WEAK_SELL** |
| < 0.55 | < 0.55 | ⚪ **HOLD** |

---

## Position Exit Rules

Active positions are monitored against three automatic exit triggers:

| Trigger | Condition |
|---|---|
| **Time-based** | Position held ≥ 10 trading days |
| **Stop-loss** | Current price ≤ entry price × 0.95 (−5%) |
| **Signal decay** | `buy_confidence` drops below 0.45 |

---

## Running the ML Pipeline

Run scripts in `src/` sequentially, or use the automation wrapper:

```bash
# Full pipeline (scrape + train + backtest)
python automation/daily_pipeline.py

# Skip scrape (use existing data)
python automation/daily_pipeline.py --skip-scrape

# Set a custom scraper window (also honored by NEPSE_SCRAPER_START_DATE)
python automation/daily_pipeline.py --start-date 2020-01-01

# Individual steps
cd src
python 01_data_audit.py
python 02_data_cleaning.py
python 03_feature_engineering.py
python 03b_fix_infinities.py
python 04_label_construction.py
python 05_walk_forward_setup.py
python 06_train_model.py        # BUY model
python 06b_train_sell_model.py  # SELL model
python 07_backtest.py
python 08_reporting.py
```

To switch the pipeline to Random Forest, set `MODEL_FAMILY=random_forest` before running the training and evaluation scripts (`06`–`08`).

The scraper uses a global start date plus a per-symbol warmup window. The per-symbol log line can therefore start later than the global start when a CSV already has recent rows. Override the global start with `--start-date` or `NEPSE_SCRAPER_START_DATE`.

---

## CI / CD

Three GitHub Actions workflows:

- **`daily-pipeline.yml`** — validates the frontend (type-check + build) and the backend (`compileall` + `pytest`) on every push/PR. The full scrape → train → backtest → report pipeline itself only runs on the daily schedule (12:15 UTC), a manual trigger, or a push to `main` that touches `scrapper/`, `automation/`, `src/`, or `requirements.txt` — not on every commit — and commits the refreshed data back to the repo.
- **`deploy.yml`** — on push to `main`, runs the backend test suite, then builds and pushes the Docker image to `ghcr.io/sudeepsigdel/fyp`.
- **`keep-alive.yml`** — weekly commit to prevent GitHub disabling scheduled workflows on an inactive repo.

Production runs on an Azure VM via `docker-compose.prod.yml` (image pulled from GHCR); see [`docs/deployment.md`](docs/deployment.md) for the full environment variable reference and deployment notes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML | XGBoost 3.2, scikit-learn, pandas, numpy |
| Backend | FastAPI 0.135, Pydantic v2, SQLAlchemy + Alembic, uvicorn |
| Auth | JWT (PyJWT + bcrypt), Google OAuth (Authlib), slowapi rate limiting |
| Database | PostgreSQL (Neon) |
| Frontend | React 18, TypeScript, Vite, `lightweight-charts`, Chart.js |
| Data | Parquet (pyarrow), pickle |
| Infra | Docker, GitHub Actions, Azure VM |

---

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, code conventions, and what CI checks before a PR can merge. Please also read the [Code of Conduct](CODE_OF_CONDUCT.md).

Found a security issue? See [SECURITY.md](SECURITY.md) instead of opening a public issue.

## License

[MIT](LICENSE) © 2026 Sudeep Sigdel

## Citation

If you use this project or its methodology in academic work, see [CITATION.cff](CITATION.cff).

---

## Disclaimer

This is a final year academic project. Signals are generated by a machine learning model trained on historical NEPSE data. **This is not financial advice.** Past performance does not guarantee future results. Always do your own research before making investment decisions.
