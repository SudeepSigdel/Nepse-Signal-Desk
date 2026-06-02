# NEPSE Signal Desk

An AI-powered stock signal platform for the Nepal Stock Exchange (NEPSE). Scrapes daily market data, trains XGBoost classifiers using walk-forward validation, and exposes a FastAPI backend + React dashboard with BUY / MODERATE / SELL / WEAK_SELL / HOLD signals.

![Python](https://img.shields.io/badge/python-3.11-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.135-green) ![React](https://img.shields.io/badge/React-18-61dafb) ![XGBoost](https://img.shields.io/badge/XGBoost-3.2-orange)

---

## How It Works

```
Daily scrape (Sharesansar / Merolagani)
    ↓
Data audit → cleaning → feature engineering → label construction
    ↓
Walk-forward training (7 folds, XGBoost or Random Forest) — BUY model + SELL model
    ↓
Backtest → reporting
    ↓
FastAPI serves signals  →  React dashboard
```

The system uses two separate classifiers, selected with `MODEL_FAMILY`:
- **BUY model** — P(stock goes up >1% in 10 days)
- **SELL model** — P(stock goes down >1% in 10 days)

Set `MODEL_FAMILY=rf` to train and load Random Forest models instead of XGBoost.

Combined, they produce a 5-level verdict: **BUY → MODERATE → HOLD → WEAK_SELL → SELL**

---

## Quick Start

### Backend

```bash
# 1. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy and configure environment
cp .env.example .env

# 4. Start the API
uvicorn app.main:app --reload
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local     # set VITE_API_BASE_URL=http://localhost:8000
npm run dev
# → http://localhost:5173
```

### Docker (both services)

```bash
docker-compose up
# Backend on :8000, mount data/ and outputs/ as volumes
```

---

## Project Structure

```
├── app/                    # FastAPI backend
│   ├── main.py             # App entry point (lifespan, CORS, routers)
│   ├── config.py           # Pydantic settings (env-driven)
│   ├── constants.py        # Confidence thresholds (single source of truth)
│   ├── routes.py           # API route handlers
│   ├── schemas.py          # Request / response Pydantic models
│   ├── data_loader.py      # Singleton: loads models + feature dataframes
│   ├── signal_service.py   # Signal generation + verdict logic
│   └── exit_rules.py       # Position exit rules (time / stop-loss / decay)
│
├── src/                    # ML pipeline (run in order)
│   ├── 01_data_audit.py
│   ├── 02_data_cleaning.py
│   ├── 03_feature_engineering.py
│   ├── 03b_fix_infinities.py
│   ├── 04_label_construction.py
│   ├── 05_walk_forward_setup.py
│   ├── 06_train_model.py       # BUY classifier
│   ├── 06b_train_sell_model.py # SELL classifier
│   ├── 07_backtest.py
│   ├── 08_reporting.py
│   └── utils.py                # Shared per_stock() utility
│
├── frontend/               # React + TypeScript dashboard
│   └── src/
│       ├── components/     # DashboardOverview, StockDetailPage, SignalCard, …
│       ├── hooks/          # useStocks, useStockDetail, useSignal
│       └── config.ts       # API base URL, refresh interval
│
├── scrapper/               # NEPSE data scraper (Sharesansar + Merolagani)
├── automation/             # Pipeline orchestration scripts
├── data/
│   ├── raw/                # Scraped CSVs (gitignored)
│   └── processed/          # Parquet files + trained model .pkl files
├── outputs/                # Charts, backtest reports
├── .github/workflows/      # daily-pipeline.yml + keep-alive.yml
├── Dockerfile              # Backend image
└── docker-compose.yml      # Local dev stack
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/stocks` | All stocks with signals, ranked by confidence |
| `GET` | `/api/stocks/{symbol}` | OHLCV candles + indicators (RSI, MACD, BB) |
| `GET` | `/api/signal/{symbol}` | BUY + SELL confidence, verdict, description |
| `POST` | `/api/positions/exit-check` | Exit guidance for a held position |
| `GET` | `/api/summary` | Top signals summary |

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

To switch the pipeline to Random Forest, set `MODEL_FAMILY=rf` before running the training and evaluation scripts.

---

## CI / CD

GitHub Actions runs the full pipeline daily at **11:15 UTC (5:00 PM Nepal time)**:

- `.github/workflows/daily-pipeline.yml` — validates Python code, runs the full pipeline driver, commits results
- `.github/workflows/keep-alive.yml` — weekly commit to prevent GitHub disabling scheduled workflows

The daily pipeline now covers the BUY model, SELL model, backtest, and reporting steps in one run.

See [`docs/deployment.md`](docs/deployment.md) for Render deployment instructions.

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML | XGBoost 3.2, scikit-learn, pandas, numpy |
| Backend | FastAPI 0.135, Pydantic v2, uvicorn |
| Frontend | React 18, TypeScript, Vite, Chart.js |
| Data | Parquet (pyarrow), pickle |
| Infra | Docker, GitHub Actions, Render |

---

## Disclaimer

This is a final year academic project. Signals are generated by a machine learning model trained on historical NEPSE data. **This is not financial advice.** Past performance does not guarantee future results. Always do your own research before making investment decisions.
