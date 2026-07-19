# Signal Architecture

Technical reference for the NEPSE Signal Desk signal generation system.

---

## Overview

The system uses a **three-layer approach**:

```
Layer 1 — Entry Signal (model-based)
  BUY model:  P(stock up >1% in 10 days)
  SELL model: P(stock down >1% in 10 days)

Layer 2 — Exit Rules (rule-based)
  Time-based:    exit after 10 trading days
  Stop-loss:     exit if price drops ≥5% from entry
  Signal decay:  exit if buy_confidence < 0.45

Layer 3 — Position Guidance (UI)
  Days held / remaining
  Current return %
  Stop-loss distance
  Active risk warnings
```

---

## Models

### Training Method: Walk-Forward Validation

The dataset is split into **9 rolling annual folds** (`data/processed/fold_config.json`), each training on an expanding window from 2012-01-01 up to the fold's cutoff, with a 20-day embargo gap before the test period to prevent leakage. Each fold produces one model file.

```
Fold 1: train [2012-01-01 → 2017-12-31] → test [2018-02-01 → 2018-12-31]
Fold 2: train [2012-01-01 → 2018-12-31] → test [2019-02-01 → 2019-12-31]
...
Fold 9: train [2012-01-01 → 2025-12-31] → test [2026-02-01 → 2026-05-02]
```

Live inference uses `model_latest*.pkl` — a copy of the most recent fold's model (the one trained on the most data). `ModelRepository` (`app/repositories/model_repository.py`) picks it automatically; numbered fold files (`model_fold1.pkl` … `model_fold9.pkl`) exist for backtesting/evaluation, not live serving.

### BUY Classifier (`model_fold*.pkl`)

- **Target:** `Label_10d = 1` if `Fwd_ret_10d > 1%` (clears NEPSE round-trip transaction costs)
- **Algorithm:** XGBoost by default, or Random Forest when `MODEL_FAMILY=random_forest`
- **Features:** 27 engineered technical and market-sentiment features (see Feature Engineering below)
- **Saved as:** `data/processed/models/model_fold{1-9}.pkl` (+ `model_latest.pkl`) for XGBoost, `_rf` suffix for Random Forest
- **Bundle keys:** `model`, `scaler`, `features`

### SELL Classifier (`model_fold*_sell.pkl`)

- **Target:** `Label_10d_sell = 1` if `Fwd_ret_10d < -1%`
- **Algorithm:** Same family as BUY (`MODEL_FAMILY=xgboost` or `random_forest`)
- **Saved as:** `data/processed/models/model_fold{1-9}_sell.pkl` (+ `model_latest_sell.pkl`) for XGBoost, `_rf_sell` suffix for Random Forest
- **Optional:** If not present, system runs in BUY-only mode (SELL/WEAK_SELL verdicts not generated)

### Relative-Strength Classifier (`model_fold*_relative.pkl`)

- **Target:** whether the stock's 10-day return beats the cross-sectional average NEPSE return
- **Algorithm:** XGBoost only
- **Features:** the 27 BUY/SELL features plus cross-sectional rank and market-volatility-regime features
- **Meaning:** comparative outperformance, not an absolute profit prediction
- **Serving:** always returned separately from the selected XGBoost/Random Forest BUY/SELL family

### Expected Performance

Mean out-of-sample AUC across the 9 folds is in the low-to-mid 0.50s for both BUY and SELL (modest edge over the 0.5 no-skill baseline; some folds land at or below 0.5). Numbers move every time the pipeline retrains and are **not** hardcoded — they're computed live from `data/processed/fold_metrics*.csv` and out-of-sample predictions by `app/repositories/evaluation_repository.py`, served via `GET /api/model-performance`, and rendered on the app's **Model Trust** page (including a calibration chart: does a stated confidence level actually track the realized outcome rate?). Check that page for current figures rather than trusting a number written here.

---

## Feature Engineering

27 features built in `src/03_feature_engineering.py`. Most come from OHLCV data; two describe optional market-wide news sentiment:

| Category | Features |
|---|---|
| **Returns/gaps** | `Ret_1d`, `Ret_3d`, `Ret_5d`, `Ret_10d`, `Ret_20d`, `Ret_momentum`, `Gap_pct` |
| **RSI** | `RSI_dist_50`, `RSI_slope_3`, `RSI_oversold`, `RSI_overbought` |
| **MACD/trend** | `MACD_hist`, `MACD_hist_slope_3`, `EMA_cross`, `Price_vs_SMA20`, `In_uptrend` |
| **Bollinger/volatility** | `BB_pctB`, `BB_width`, `ATR_ratio`, `Vol_10d`, `HL_range_pct` |
| **Volume** | `Volume_ratio`, `Volume_spike`, `OBV_slope_5`, `OBV_slope_norm` |
| **Market sentiment** | `Sentiment_score`, `Sentiment_available` |

The sentiment score is market-wide, uses FinBERT-scored headlines when available, and falls back to a neutral value with `Sentiment_available = 0`; it must not be interpreted as company-specific news analysis.

---

## Confidence Thresholds

Single source of truth in [`app/constants.py`](../app/constants.py):

```python
THRESHOLD_HIGH   = 0.65   # Strong signal
THRESHOLD_MEDIUM = 0.55   # Moderate signal
THRESHOLD_LOW    = 0.45   # Signal decay threshold (exit trigger)
```

### Verdict Logic

```python
if buy_conf >= 0.65:              → BUY
elif buy_conf >= 0.55:            → MODERATE
elif sell_conf >= 0.65:           → SELL
elif sell_conf >= 0.55:           → WEAK_SELL
else:                             → HOLD

# Conflicting signals (both high) → HOLD
```

---

## Exit Rules

Defined in [`app/services/exit_rules.py`](../app/services/exit_rules.py), called from `POST /api/positions/exit-check` (route in `app/api/routes/positions.py`).

| Rule | Trigger | `exit_type` |
|---|---|---|
| Time-based | `days_held >= 10` | `time_based` |
| Stop-loss | `(current_price / entry_price - 1) <= -0.05` | `stop_loss` |
| Signal decay | `buy_confidence < 0.45` | `signal_decay` |

Priority: **stop_loss > time_based > signal_decay**

### Risk Warnings (pre-exit)

Shown in the position tracker UI before an exit triggers:

- Days remaining ≤ 2 → "Approaching 10-day exit"
- Stop-loss distance < 1.5% → "Close to stop-loss"
- `buy_confidence < 0.50` → "Signal weakening"

---

## Data Flow

```
scrapper/  →  data/raw/*.csv
               ↓
src/01  →  combined parquet (all_stocks_combined.parquet)
src/02  →  cleaned parquet  (all_stocks_clean.parquet)
src/03  →  feature parquet  (all_stocks_features.parquet)
src/04  →  labeled parquet  (all_stocks_labeled.parquet)
src/05  →  fold config      (fold_config.json)
src/06  →  BUY models       (data/processed/models/model_fold*.pkl or model_fold*_rf.pkl)
src/06b →  SELL models      (data/processed/models/model_fold*_sell.pkl or model_fold*_rf_sell.pkl)
src/07  →  backtest results (outputs/strategy_metrics*.csv)
src/08  →  reports + charts (data/processed/report/*.csv, *.png)
               ↓
app/repositories/model_repository.py   →  loads model_latest*.pkl + scaler + features
app/repositories/stock_repository.py   →  loads all_stocks_features.parquet
app/repositories/evaluation_repository.py  →  loads fold metrics, OOS calibration, backtest tables
app/services/signal_service.py         →  computes buy_confidence, sell_confidence, verdict
app/api/routes/*.py                    →  serves everything via FastAPI (signals, stocks,
                                           positions, model-performance, auth, watchlist, holdings)
```

---

## API Response Example

```json
GET /api/signal/NABIL

{
  "symbol": "NABIL",
  "date": "2025-05-14",
  "close": 1245.50,
  "buy_confidence": 0.71,
  "sell_confidence": 0.22,
  "verdict": "Strong buy signal",
  "verdict_color": "green",
  "description": "Stock shows strong upward momentum...",
  "active_signals": ["RSI Oversold Recovery", "MACD Bullish Cross", "Volume Surge"],
  "indicators": {
    "rsi": 38.4,
    "rsi_zone": "Oversold",
    "macd": 12.3,
    "macd_signal": 8.1,
    "macd_hist": 4.2,
    "macd_bias": "Bullish",
    "bb_pctb": 0.18,
    "bb_zone": "Lower Band",
    "in_uptrend": true,
    "volume_ratio": 1.8,
    "volume_note": "Above average"
  },
  "thresholds": {
    "buy_high": 0.65,
    "buy_medium": 0.55,
    "buy_low": 0.45
  }
}
```
