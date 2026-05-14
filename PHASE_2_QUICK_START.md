# Phase 2: Quick Start — Training & Verification

**Status:** ✅ Backend ready  
**Next:** Run training pipeline (30 minutes - 3 hours total)

---

## Step 1: Generate SELL Labels (5 minutes)

```bash
cd src/
python 04_label_construction.py
```

**What it does:**
- Reads `all_stocks_features.parquet`
- Creates `Label_10d_sell` column with mirror logic:
  ```
  Label_10d_sell = 1 if (next 10-day return < -1%)
  Label_10d_sell = 0 otherwise
  ```
- Outputs label distribution stats
- Saves to `all_stocks_labeled.parquet`

**Expected output shows both BUY and SELL labels created**

---

## Step 2: Train SELL Classifiers (30 minutes - 1 hour)

```bash
python src/06b_train_sell_model.py
```

**What it does:**
- Reads `all_stocks_labeled.parquet` with SELL labels
- Trains 7 XGBoost models (one per fold)
- Saves each as `model_fold{0-6}_sell.pkl`
- Generates performance metrics

**Expected output:**
```
Mean AUC across folds: 0.51 ± 0.01
(This is normal - financial data is hard to predict)
```

---

## Step 3: Verify Models Load (1 minute)

```bash
python -c "
from app.data_loader import DataLoader
dl = DataLoader()
print('BUY model:', type(dl.model_buy).__name__ if dl.model_buy else 'MISSING')
print('SELL model:', type(dl.model_sell).__name__ if dl.model_sell else 'MISSING')
"
```

**Expected:**
```
BUY model: XGBClassifier
SELL model: XGBClassifier
```

---

## Step 4: Test API (1 minute)

```bash
# Start API
uvicorn app.main:app --reload --port 8000 &

# Test endpoint
curl http://localhost:8000/api/signal/ABC | jq '.buy_confidence, .sell_confidence'
```

**Expected:** Two confidence scores returned

---

## Complete Command Sequence

```bash
cd src/
python 04_label_construction.py
python 06b_train_sell_model.py
cd ../
python -c "from app.data_loader import DataLoader; DataLoader()"
uvicorn app.main:app --port 8000 &
curl http://localhost:8000/api/signal/ABC | jq '.'
```

---

## What Happens After

✅ API returns 5-level verdicts (BUY/MODERATE/SELL/WEAK_SELL/HOLD)  
✅ Both buy and sell confidences in response  
✅ Ready for Phase 3 (frontend updates)  

See `PHASE_2_IMPLEMENTATION.md` for full technical details.

**Modification to `src/04_label_construction.py`:**

Add this code right after BUY label creation:

```python
# SELL Label: Mirror logic with inverted threshold
# A SELL signal when stock drops more than 1% in next 10 days
Label_10d_sell = (Fwd_ret_10d < -0.01).astype(int)

# Verify balance
print(f"BUY signals (forward return > +1%): {Label_10d_buy.sum()}")
print(f"SELL signals (forward return < -1%): {Label_10d_sell.sum()}")
print(f"Total samples: {len(Label_10d_buy)}")
```

**Expected output:**
```
BUY signals: ~2500 (rough estimate)
SELL signals: ~2500 (roughly balanced)
Total samples: ~15000
```

### Step 3: Update Model Training (1 hour)

**File:** `src/06_train_model.py`

**What to do:**

1. Find the main training loop (look for `for fold in range(7):`)
2. After BUY model training, add SELL model training:

```python
# After buy model training loop...

# TRAIN SELL MODEL (SELL classifier)
print("\n" + "="*50)
print("TRAINING SELL CLASSIFIERS (7 folds)")
print("="*50)

for fold in range(7):
    print(f"\nFold {fold+1}/7")
    
    # Get fold data
    X_train, y_train, X_test, y_test = get_fold_data_sell(fold)  # NEW: use SELL labels
    
    # Train SELL model
    sell_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    sell_model.fit(X_train, y_train)
    
    # Evaluate
    train_acc = sell_model.score(X_train, y_train)
    test_acc = sell_model.score(X_test, y_test)
    
    print(f"  Train Accuracy: {train_acc:.3f}")
    print(f"  Test Accuracy: {test_acc:.3f}")
    
    # Save SELL model
    joblib.dump(sell_model, f'models/model_fold{fold}_sell.pkl')
    print(f"  Saved: models/model_fold{fold}_sell.pkl")

print("\n✓ All SELL models trained and saved")
```

**Expected output:**
```
TRAINING SELL CLASSIFIERS (7 folds)
==================================================

Fold 1/7
  Train Accuracy: 0.526
  Test Accuracy: 0.512
  Saved: models/model_fold0_sell.pkl
  
Fold 2/7
  Train Accuracy: 0.531
  Test Accuracy: 0.515
  ...
  
✓ All SELL models trained and saved
```

### Step 4: Update Data Loader (30 min)

**File:** `app/data_loader.py`

**Modification:**

Find where BUY models are loaded:

```python
# Current (BUY only)
self.model = joblib.load(f'models/model_fold{fold}_buy.pkl')
```

Update to load both:

```python
# Updated (both BUY and SELL)
self.buy_model = joblib.load(f'models/model_fold{fold}_buy.pkl')
self.sell_model = joblib.load(f'models/model_fold{fold}_sell.pkl')
```

Also update the property:

```python
@property
def model(self):
    """Return buy model (for backward compatibility)"""
    return self.buy_model

@property
def sell_model(self):
    """Return sell model"""
    return self._sell_model
```

### Step 5: Update Signal Service (30 min)

**File:** `app/signal_service.py`

**Add method to compute both confidences:**

```python
def get_buy_and_sell_confidence(self, symbol: str) -> Tuple[Optional[float], Optional[float]]:
    """Compute both buy and sell confidence scores."""
    buy_conf = self.compute_confidence(symbol, model='buy')
    sell_conf = self.compute_confidence(symbol, model='sell')
    return buy_conf, sell_conf
```

**Update verdict logic to 5 levels:**

```python
def get_verdict_with_sell(self, buy_conf: float, sell_conf: float) -> Tuple[str, str, str]:
    """
    Return (verdict, color, description) with 5 levels:
    - BUY: buy >= 0.65 and sell < 0.55
    - MODERATE: buy >= 0.55 and sell < 0.55
    - SELL: sell >= 0.65 and buy < 0.55
    - WEAK_SELL: sell >= 0.55 and buy < 0.55
    - HOLD: else (uncertain or conflicting)
    """
    
    if buy_conf >= 0.65 and sell_conf < 0.55:
        return "BUY", "green", "Strong bullish pattern"
    elif buy_conf >= 0.55 and sell_conf < 0.55:
        return "MODERATE", "orange", "Moderate bullish pattern"
    elif sell_conf >= 0.65 and buy_conf < 0.55:
        return "SELL", "red", "Strong bearish pattern"
    elif sell_conf >= 0.55 and buy_conf < 0.55:
        return "WEAK_SELL", "orange-red", "Moderate bearish pattern"
    else:
        return "HOLD", "gray", "Uncertain - conflicting signals or no edge"
```

### Step 6: Testing (30 min)

**Test the new models:**

```python
# Test that models exist
import joblib
for fold in range(7):
    buy = joblib.load(f'models/model_fold{fold}_buy.pkl')
    sell = joblib.load(f'models/model_fold{fold}_sell.pkl')
    print(f"✓ Fold {fold}: Both models loaded")

# Test that data loader works
from app.data_loader import DataLoader
loader = DataLoader()
print(f"✓ DataLoader loaded")
print(f"  Buy model: {loader.buy_model is not None}")
print(f"  Sell model: {loader.sell_model is not None}")

# Test predictions
X_test = loader.get_features_for_symbol("AAPL")
if X_test is not None:
    buy_prob = loader.buy_model.predict_proba(X_test)[:, 1]
    sell_prob = loader.sell_model.predict_proba(X_test)[:, 1]
    print(f"✓ Predictions work")
    print(f"  Buy confidence: {buy_prob[0]:.3f}")
    print(f"  Sell confidence: {sell_prob[0]:.3f}")
```

---

## Detailed Timeline

### Hour 1: Label Creation
- [ ] 15 min: Read current label construction
- [ ] 15 min: Add SELL labels  
- [ ] 30 min: Verify label balance

### Hour 2: Model Training
- [ ] 60 min: Train 7 SELL models (models will run in parallel if system allows)
- [ ] Result: 7 files `model_fold*_sell.pkl`

### Hour 3: Integration
- [ ] 30 min: Update DataLoader
- [ ] 30 min: Update SignalService with 5-level logic

### Hour 4: Testing & Polish
- [ ] 30 min: Test both models load correctly
- [ ] 30 min: Verify predictions reasonable
- [ ] 30 min: Update API response schema if needed

---

## Important Notes

### Threshold Consistency
- BUY threshold: 1% gain in 10 days (already used)
- SELL threshold: 1% loss in 10 days (mirror logic)
- This is symmetric and fair ✅

### Expected Accuracy
- Both models should achieve ~51-53% accuracy
- This is slightly above random (50%) ✅
- Means they learned a real pattern
- ❌ Do NOT expect 80%+ accuracy (financial data is noisy)

### Model Save Location
- Buy models: `models/model_fold0_buy.pkl` ... `model_fold6_buy.pkl`
- Sell models: `models/model_fold0_sell.pkl` ... `model_fold6_sell.pkl`
- Total: 14 model files

### Files Modified/Created
1. `src/04_label_construction.py` — Add SELL labels
2. `src/06_train_model.py` — Add SELL training loop
3. `app/data_loader.py` — Load both models
4. `app/signal_service.py` — 5-level verdict logic

### Verification Checklist
- [ ] All 7 SELL models trained and saved
- [ ] DataLoader loads both models without error
- [ ] API endpoint still works
- [ ] Tests pass with both models
- [ ] 5-level verdicts appear correctly

---

## Success Criteria

✅ If you can do this:

```python
from app.data_loader import DataLoader

loader = DataLoader()
X = loader.get_features_for_symbol("AAPL")

buy_conf = loader.buy_model.predict_proba(X)[:, 1][0]
sell_conf = loader.sell_model.predict_proba(X)[:, 1][0]

# Both should be between 0 and 1
assert 0 <= buy_conf <= 1
assert 0 <= sell_conf <= 1

print(f"✓ Both models working!")
print(f"  BUY:  {buy_conf:.2f}")
print(f"  SELL: {sell_conf:.2f}")
```

Then Phase 2 is complete! ✅

---

## Troubleshooting

### Training Takes Too Long
- Expected: 2-3 hours for 7 models
- If >4 hours: Check system resources
- Can run folds in parallel if available

### Models Don't Exist
- Check `models/` directory exists
- Check paths in code match actual files
- Verify fold numbering (0-6, not 1-7)

### Accuracy Too High (>80%)
- Likely overfitting
- Check that train/test split is correct
- Verify you're not using future data

### Accuracy Too Low (<50%)
- Model learned inverse pattern
- Check label logic is correct
- Verify data isn't corrupted

---

## Next After Phase 2

Once sell models are trained:

### Phase 3: UI Updates (2 hours)
1. Update dashboard to show 5 verdicts
2. Add sell_confidence display
3. Update GlossaryModal with SELL explanation
4. Update RiskPanel with sell signal accuracy

### Backlog (Optional)
- Add company info panel (sector, market cap)
- Add price target calculations
- Add educational section

---

## Reference Documents

- `HONEST_SIGNAL_ARCHITECTURE.md` — Why two models
- `docs/THRESHOLD_UNIFICATION.md` — Threshold choices
- `EXIT_RULES_INTEGRATION.py` — Examples
- `PHASE_3_CHECKLIST.md` — Phase 2 details

---

**You've got this! Phase 2 is straightforward: add 10 lines of label code, train for 2 hours, integrate for 1 hour. 🚀**
