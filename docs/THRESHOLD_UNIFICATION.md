# Threshold Unification & Signal Label Corrections

## Summary of Changes

This update addresses two important issues identified in model accuracy and signal labeling:

### 1. **Unified Confidence Thresholds** ✅

**Problem:** The original code had three different threshold cutoffs scattered across files:
- Summary table: Used 0.55, 0.60, 0.65
- Fold performance evaluation: Used 0.55
- Signal interpreter display: Used ≥ 0.60

**Solution:** Centralized all thresholds in `app/constants.py`:
```python
THRESHOLD_HIGH = 0.65      # Strong buy signal
THRESHOLD_MEDIUM = 0.55    # Moderate buy signal
THRESHOLD_LOW = 0.45       # Weak signal (avoid)
```

**Where Used:**
- ✅ `app/signal_service.py` — Signal generation
- ✅ `app/routes.py` — API endpoints (stocks, summary, signals)
- ✅ Frontend components can import from constants.py (future)

**Benefit:** Single source of truth. Changes to thresholds update everywhere automatically.

---

### 2. **Corrected Signal Labels** 🔴➡️🟠

**Problem:** The red signal was labeled "SELL", which is misleading. The model outputs **buy probability**, not sell signals.
- Confidence < 0.45 means: "Low probability this is a GOOD BUY"
- NOT: "Confirmed sell opportunity"

**Solution:** Updated signal verdict labels:

| Confidence | Old Label | New Label | Meaning |
|---|---|---|---|
| ≥ 0.65 | Strong Buy ✅ | Strong Buy 🟢 | Good buy opportunity |
| 0.55-0.65 | Moderate Signal ✅ | Moderate Buy 🟠 | Some potential, wait for better entry |
| 0.45-0.55 | Neutral | Weak Signal ⚪ | Low buy confidence, uncertain |
| < 0.45 | SELL ❌ | AVOID 🔴 | Not a good buy right now |

**Updated Descriptions:**

**GREEN (≥ 0.65): "Strong buy signal"**
> "Stock shows strong upward momentum 📈. More buyers than sellers. Our AI thinks this stock will likely go up in the next 10 days. This is a good time to consider buying. Remember: Check company news first and set a stop-loss 5-10% below to limit losses."

**ORANGE (0.55-0.65): "Moderate buy signal"**
> "Stock shows some bullish signs 📊, but not strong enough for a confident buy. Wait for a better entry price (a 5% dip) or more confirmation signals. If you buy now, use a smaller position size."

**GRAY (0.45-0.55): "Weak signal"**
> "We can't see a clear reason to buy this stock right now ⚪. This stock is in a holding pattern with no strong momentum either direction. Better opportunities might appear later. If you already own it, hold or consider taking some profits."

**RED (< 0.45): "Avoid for now"**
> "Stock shows bearish signals 📉. More sellers than buyers. Our AI thinks this stock will likely go down in the next 10 days. This is NOT a good time to buy. If you already own it, consider selling into strength (during rallies). Otherwise, stay away and look for better opportunities."

---

### 3. **Files Modified**

- ✅ `app/constants.py` — NEW: Central threshold configuration
- ✅ `app/signal_service.py` — Use THRESHOLD_* constants, updated verdicts
- ✅ `app/routes.py` — Use THRESHOLD_* constants for API filtering
- ✅ `frontend/src/components/SignalCard.tsx` — Updated action text (AVOID instead of SELL)
- ✅ `frontend/src/components/GlossaryModal.tsx` — Updated red signal explanation

---

### 4. **Accuracy Notes (Transparent to Users)**

The model accuracy stats shown to users are realistic:
- **Overall accuracy:** ~55% (predicts direction correctly on average)
- **High confidence signals:** ~62% accuracy (when confidence ≥ 0.65)
- **Lookback period:** 10 days (model predicts 10-day returns)

These are disclosed to users in the RiskPanel component to set proper expectations.

---

### 5. **Key Takeaway**

The model outputs a **buy opportunity probability** (0-1). Users should interpret signals as:
- 🟢 **Green:** "Good time to buy"
- 🟠 **Orange:** "Maybe buy, but wait for better entry"
- ⚪ **Gray:** "Uncertain, skip this stock"
- 🔴 **Red:** "Bad time to buy, avoid new positions"

This is honest about what the model actually does, without overstating its capabilities.

---

## Testing

To verify the changes:

1. **Backend API test:**
   ```bash
   python -m uvicorn app.main:app --reload
   curl http://localhost:8000/api/signal/NEPSE
   # Verify verdict, verdict_color, and description are accurate
   ```

2. **Frontend test:**
   - Open dashboard
   - Click on a stock with red signal
   - Verify it shows "AVOID" not "SELL"
   - Verify action text says "Don't buy right now"

3. **Constants test:**
   ```python
   from app.constants import THRESHOLD_HIGH, THRESHOLD_MEDIUM, THRESHOLD_LOW
   print(f"High: {THRESHOLD_HIGH}, Medium: {THRESHOLD_MEDIUM}, Low: {THRESHOLD_LOW}")
   # Should output: High: 0.65, Medium: 0.55, Low: 0.45
   ```
