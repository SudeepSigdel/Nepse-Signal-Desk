# Phase 2: SELL Classifier — Backend Integration Complete ✅

## TL;DR
**Backend is ready for SELL model training.** All code changes complete. Waiting for training pipeline to run (2-3 hours).

---

## What's Done

### ✅ Code Changes (100% Complete)

1. **Add SELL Labels** — `src/04_label_construction.py`
   - Added: `Label_10d_sell = (Fwd_ret_10d < -1%)`
   - Mirror of BUY label logic

2. **Train SELL Models** — `src/06b_train_sell_model.py` (NEW)
   - Trains 7-fold SELL classifiers
   - Saves as `model_fold*_sell.pkl`
   - Same hyperparameters as BUY

3. **Dual Model Loading** — `app/data_loader.py`
   - Loads `model_fold*.pkl` (BUY)
   - Loads `model_fold*_sell.pkl` (SELL)
   - Graceful fallback if SELL missing

4. **Dual Confidence Scoring** — `app/signal_service.py`
   - `compute_confidence()` → BUY score
   - `compute_sell_confidence()` → SELL score
   - 5-level verdict logic

5. **API Schema Updates** — `app/schemas.py`
   - `buy_confidence` + `sell_confidence` in response
   - Updated thresholds structure

---

## What's Next

### Phase 2 Training (You):
```bash
# Step 1: Add SELL labels (5 min)
python src/04_label_construction.py

# Step 2: Train SELL models (2-3 hours)
python src/06b_train_sell_model.py

# Step 3: Verify models loaded (1 min)
python -c "from app.data_loader import DataLoader; dl = DataLoader(); print(f'BUY: {dl.model_buy}, SELL: {dl.model_sell}')"
```

### Phase 3 (UI Updates):
- [ ] Show 5-level verdicts in dashboard
- [ ] Display SELL confidence gauge
- [ ] Update glossary with SELL explanation
- [ ] End-to-end testing

---

## 5-Level Signal System

```
Confidence     Verdict           Color    Action
─────────────────────────────────────────────────
BUY >= 0.65   🟢 Strong BUY      Green    Buy now
BUY 0.55-0.65 🟠 Moderate BUY    Orange   Wait/smaller
SELL >= 0.65  🔴 SELL            Red      Don't buy
SELL 0.55-0.65 🟡 Weak SELL      Yellow   Risky
else          ⚪ HOLD            Gray     No action
```

---

## Files Created/Modified

```
src/
├── 04_label_construction.py    [MODIFIED] Add SELL labels
└── 06b_train_sell_model.py     [NEW] Train SELL classifiers

app/
├── data_loader.py              [MODIFIED] Load both models
├── signal_service.py           [MODIFIED] Dual confidence + 5-level verdicts
└── schemas.py                  [MODIFIED] API contracts
```

---

## Key Changes at a Glance

### DataLoader
```python
# Before
self.model = None
self.scaler = None

# After
self.model_buy = None
self.model_sell = None
self.scaler_buy = None
self.scaler_sell = None

# Backward compat
@property
def model(self):
    return self.model_buy
```

### SignalService
```python
# Before
confidence = self.compute_confidence(symbol)
verdict, color, desc = self.get_verdict(confidence)

# After
buy_conf = self.compute_confidence(symbol)
sell_conf = self.compute_sell_confidence(symbol)
verdict, color, desc = self.get_verdict(buy_conf, sell_conf)
```

### API Response
```python
# Before
{"confidence": 0.72, "verdict": "Strong buy signal"}

# After
{
  "buy_confidence": 0.72,
  "sell_confidence": 0.28,
  "verdict": "Strong buy signal",  # 5-level logic applied
  "thresholds": {"buy_high": 0.65, "buy_medium": 0.55, "buy_low": 0.45}
}
```

---

## Testing Command Checklist

```bash
# 1. Run label construction (creates SELL labels)
python src/04_label_construction.py

# 2. Check SELL label distribution
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/all_stocks_labeled.parquet')
print(df['Label_10d_sell'].value_counts())
"

# 3. Train SELL models (2-3 hours)
python src/06b_train_sell_model.py

# 4. Verify models created
ls -la data/processed/models/model_fold*_sell.pkl

# 5. Test DataLoader loads both
python -c "
from app.data_loader import DataLoader
dl = DataLoader()
print(f'BUY model: {type(dl.model_buy).__name__}')
print(f'SELL model: {type(dl.model_sell).__name__}')
print(f'Symbols: {len(dl.all_symbols)}')
"

# 6. Test API endpoint (after training)
curl http://localhost:8000/api/signal/ABC | jq '.buy_confidence, .sell_confidence'
```

---

## Why This Design?

**Problem:** Binary classifier can only predict "buy" or "not buy", not true SELL signals.

**Solution:** Train two symmetric models:
- BUY: P(stock up >1% in 10d)
- SELL: P(stock down >1% in 10d)

**Benefit:**
- ✅ Symmetric and honest about what each model does
- ✅ Each score is independent (both can be high or low)
- ✅ Combines entry (models) + exit (rules) cleanly
- ✅ Gracefully degraded if SELL model missing

**Expected Accuracy:**
- BUY model AUC: ~0.58-0.62 (current)
- SELL model AUC: ~0.50-0.53 (new, slightly above random)

This is normal for financial data. Short-term downside is hard to predict.

---

## Status Tracker

| Task | Status | Time | Owner |
|------|--------|------|-------|
| Label construction changes | ✅ Done | 10 min | Code ✓ |
| SELL training script | ✅ Done | 30 min | Code ✓ |
| DataLoader dual models | ✅ Done | 45 min | Code ✓ |
| SignalService refactor | ✅ Done | 60 min | Code ✓ |
| Schema updates | ✅ Done | 15 min | Code ✓ |
| **Run training pipeline** | ⏳ Pending | 3 hours | You |
| Frontend updates | ⏳ Phase 3 | TBD | Next |
| E2E testing | ⏳ Phase 3 | 1 hour | Next |

---

## Backward Compatibility

✅ **Existing code still works:**
- `loader.model` → returns `model_buy` (via property)
- `loader.scaler` → returns `scaler_buy` (via property)
- Existing routes work without changes
- SELL model is optional (gracefully missing)

---

## Next Session

When ready to proceed:
1. Run `python src/04_label_construction.py`
2. Run `python src/06b_train_sell_model.py`
3. Verify models with curl test
4. Move to Phase 3: Frontend updates

Questions? Check `PHASE_2_IMPLEMENTATION.md` for full details.

