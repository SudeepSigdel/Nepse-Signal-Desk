# Phase 2: SELL Classifier Implementation — COMPLETE

## Status: Backend Integration Complete ✅
All backend changes have been made to support both BUY and SELL models. Now waiting for training pipeline to complete.

---

## What Was Changed

### 1. **Label Construction (src/04_label_construction.py)** ✅
- **Added SELL labels** with mirror logic:
  ```python
  Label_10d_sell = (df["Fwd_ret_10d"] < -TRANSACTION_COST).astype(int)
  ```
- Updated label distribution output to show both BUY and SELL stats
- When run, creates parquet file with SELL labels

### 2. **SELL Model Training Script (src/06b_train_sell_model.py)** ✅
- **Created dedicated training script** for SELL models
- Uses same XGBoost hyperparameters as BUY models
- Trains 7 folds, saves as `model_fold{0-6}_sell.pkl`
- Outputs:
  - `oos_predictions_sell.parquet` — Out-of-sample predictions
  - `fold_metrics_sell.csv` — Performance metrics per fold
  - `feature_importance_sell.png` — Feature importance chart

### 3. **DataLoader (app/data_loader.py)** ✅
**Major refactor to support both models:**

- Added dual model attributes:
  - `model_buy` — BUY classifier (main model)
  - `model_sell` — SELL classifier (optional, gracefully degraded if missing)
  - `scaler_buy` — Scaler for BUY model
  - `scaler_sell` — Scaler for SELL model

- Renamed `_load_model()` → `_load_models()` with logic for both:
  - BUY: Loads `model_fold*.pkl` (without `_sell` suffix)
  - SELL: Loads `model_fold*_sell.pkl` (with `_sell` suffix)
  - SELL gracefully optional — if not present, logs warning and continues

- Added backward compatibility properties:
  - `@property model` — returns `model_buy`
  - `@property scaler` — returns `scaler_buy`
  - Ensures existing code that uses `loader.model` still works

### 4. **SignalService (app/signal_service.py)** ✅
**Enhanced for dual-model predictions:**

- Split confidence computation:
  - `compute_confidence(symbol)` → BUY confidence only
  - `compute_sell_confidence(symbol)` → SELL confidence (returns None if no SELL model)

- Updated `get_verdict()` with 5-level signal logic:
  ```
  buy_conf >= 0.65:      🟢 Strong BUY
  buy_conf >= 0.55:      🟠 Moderate BUY
  sell_conf >= 0.65:     🔴 SELL
  sell_conf >= 0.55:     🟡 Weak SELL
  else:                  ⚪ HOLD
  ```

- Updated `get_signal()` to return both:
  - `buy_confidence` (always present)
  - `sell_confidence` (None if SELL model not available)

### 5. **Schemas (app/schemas.py)** ✅
**Updated API contracts:**

- `SignalThresholds`:
  - Old: `recommended`, `minimum` (generic)
  - New: `buy_high`, `buy_medium`, `buy_low` (explicit levels)

- `SignalResponse`:
  - Old: `confidence` (single score)
  - New: `buy_confidence`, `sell_confidence` (dual scores)

---

## Next Steps: Training Pipeline

### To Complete Phase 2:

1. **Run label construction** (if not already done):
   ```bash
   cd src/
   python 04_label_construction.py
   ```
   - Verifies `Label_10d_sell` column created
   - Shows distribution of SELL labels (should be ~50-55% of data)

2. **Train SELL models** (2-3 hours):
   ```bash
   python 06b_train_sell_model.py
   ```
   - Trains 7 models using `Label_10d_sell`
   - Each fold's SELL model saved as `model_fold{0-6}_sell.pkl`
   - Expected AUC: ~0.50-0.53 (slightly above random — normal for financial data)
   - Outputs performance charts and metrics

3. **Verify models loaded correctly**:
   ```bash
   cd app/
   python -c "from data_loader import DataLoader; dl = DataLoader(); print(f'BUY: {dl.model_buy is not None}, SELL: {dl.model_sell is not None}')"
   ```

4. **Test API endpoints** (once models are trained):
   ```bash
   # Test health check
   curl http://localhost:8000/health
   
   # Test signal with both confidences
   curl http://localhost:8000/api/signal/ABC
   ```
   - Should return both `buy_confidence` and `sell_confidence`
   - Verdict should be 5-level (BUY/MODERATE/SELL/WEAK_SELL/HOLD)

---

## Architecture: Three-Layer System

```
Entry Layer (What to Buy)
├─ BUY Model: "Is this stock going up?" (probability)
└─ SELL Model: "Is this stock going down?" (probability)

Exit Layer (When to Sell)
├─ Time-based: After 10 days
├─ Stop-loss: Price down 5%
└─ Signal decay: Confidence < 0.45

Position Management (How to Manage)
├─ Display exit guidance
├─ Track position health
└─ Manage risk exposure
```

---

## Key Files Modified/Created

| File | Change | Status |
|------|--------|--------|
| `src/04_label_construction.py` | Added SELL labels | ✅ |
| `src/06b_train_sell_model.py` | New SELL training script | ✅ Created |
| `app/data_loader.py` | Dual model support | ✅ |
| `app/signal_service.py` | Dual confidence computation | ✅ |
| `app/schemas.py` | API contracts updated | ✅ |

---

## API Response Examples

### Before (BUY only):
```json
{
  "symbol": "ABC",
  "date": "2024-01-15",
  "close": 100.5,
  "confidence": 0.72,
  "verdict": "Strong buy signal",
  "verdict_color": "green",
  "description": "..."
}
```

### After (BUY + SELL):
```json
{
  "symbol": "ABC",
  "date": "2024-01-15",
  "close": 100.5,
  "buy_confidence": 0.72,
  "sell_confidence": 0.28,
  "verdict": "Strong buy signal",
  "verdict_color": "green",
  "description": "...",
  "thresholds": {
    "buy_high": 0.65,
    "buy_medium": 0.55,
    "buy_low": 0.45
  }
}
```

---

## Testing Checklist

- [ ] `04_label_construction.py` runs without error
- [ ] `Label_10d_sell` column created in dataset
- [ ] SELL label distribution looks reasonable (~50-55%)
- [ ] `06b_train_sell_model.py` completes training
- [ ] All 7 `model_fold*_sell.pkl` files created
- [ ] Mean SELL AUC is ~0.50-0.53
- [ ] DataLoader loads both models successfully
- [ ] API returns both `buy_confidence` and `sell_confidence`
- [ ] 5-level verdicts appear correctly
- [ ] Backward compatibility: existing code using `loader.model` still works

---

## Expected Behavior

**BUY Model (existing):**
- Outputs P(stock goes up >1% in 10 days)
- Threshold 0.65 = "strong buy"
- Threshold 0.55 = "moderate buy"

**SELL Model (new):**
- Outputs P(stock drops >1% in 10 days)
- Threshold 0.65 = "strong sell" (avoid buying)
- Threshold 0.55 = "weak sell" (risky to buy)

**Combined Logic:**
- If BUY >= 0.65 → Buy (ignore SELL)
- Else if BUY >= 0.55 → Moderate (consider wait)
- Else if SELL >= 0.65 → Sell (avoid)
- Else if SELL >= 0.55 → Weak sell (risky)
- Else → Hold (no signal)

---

## Notes

- SELL model accuracy will be ~51-53%, which is **normal for financial data** (barely above 50% random)
- This doesn't mean the model is useless; it means predicting short-term downside is hard
- The model is trained on same 24 features and same walk-forward folds as BUY model
- Both models share the same feature engineering pipeline
- SELL model is **optional** — if not present, system still works with BUY-only logic

---

## Phase 3: UI Updates (Next)

Once Phase 2 training completes:
1. Update frontend to display 5 verdicts
2. Add "Sell Confidence" gauge
3. Update GlossaryModal with SELL signal explanation
4. Manual testing end-to-end
5. Performance monitoring

