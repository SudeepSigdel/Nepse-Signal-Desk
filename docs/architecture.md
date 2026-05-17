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

The dataset is split into **7 chronological folds** with an embargo gap between training and test periods to prevent data leakage. Each fold produces one model file.

```
Fold 1: train [2010–2018] → test [2019]
Fold 2: train [2010–2019] → test [2020]
...
Fold 7: train [2010–2024] → test [2025]
```

Inference uses the **most recent fold** (fold 6, 0-indexed) — the model with the most training data.

### BUY Classifier (`model_fold*.pkl`)

- **Target:** `Label_10d = 1` if `Fwd_ret_10d > 1%` (clears NEPSE round-trip transaction costs)
- **Algorithm:** XGBoost by default, or Random Forest when `MODEL_FAMILY=rf`
- **Features:** 24 engineered features (see Feature Engineering below)
- **Saved as:** `data/processed/models/model_fold{0-6}.pkl` for XGBoost, `model_fold{0-6}_rf.pkl` for Random Forest
- **Bundle keys:** `model`, `scaler`, `features`

### SELL Classifier (`model_fold*_sell.pkl`)

- **Target:** `Label_10d_sell = 1` if `Fwd_ret_10d < -1%`
- **Algorithm:** Same family as BUY (`MODEL_FAMILY=xgboost` or `rf`)
- **Saved as:** `data/processed/models/model_fold{0-6}_sell.pkl` for XGBoost, `model_fold{0-6}_rf_sell.pkl` for Random Forest
- **Optional:** If not present, system runs in BUY-only mode (SELL/WEAK_SELL verdicts not generated)

### Expected Performance

| Model | Metric | Value |
|---|---|---|
| BUY | Overall accuracy | ~55% |
| BUY | High-confidence accuracy (≥0.65) | ~62% |
| SELL | Overall accuracy | ~51–53% |

Both scores are above the 50% random baseline. Predicting short-term downside is inherently harder than upside for NEPSE.

---

## Feature Engineering

24 features built from raw OHLCV data in `src/03_feature_engineering.py`:

| Category | Features |
|---|---|
| **Returns** | `Log_Return`, `Ret_3d`, `Ret_5d`, `Ret_10d`, `Ret_20d`, `Ret_momentum` |
| **RSI** | `RSI_14`, `RSI_dist_50`, `RSI_momentum` |
| **MACD** | `MACD`, `MACD_Signal`, `MACD_Hist`, `MACD_cross` |
| **Bollinger** | `BB_pctB`, `BB_width`, `BB_squeeze` |
| **Volume** | `Volume_ratio`, `Volume_trend` |
| **Trend** | `SMA20_dist`, `Price_vs_SMA50`, `in_uptrend` |
| **Volatility** | `ATR_14`, `Volatility_20d` |

> `Ret_momentum = (Ret_3d − Ret_10d) / 2` — short-term vs medium-term divergence

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

Defined in [`app/exit_rules.py`](../app/exit_rules.py), called from `POST /api/positions/exit-check`.

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
src/08  →  reports + charts (outputs/*.png)
               ↓
app/data_loader.py  →  loads latest fold model + features into memory
app/signal_service.py  →  computes buy_confidence, sell_confidence, verdict
app/routes.py  →  serves via FastAPI
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
