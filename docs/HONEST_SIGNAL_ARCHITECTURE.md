# Honest Signal Architecture: Buy Model + Exit Rules + Sell Classifier

## The Problem We Solved

**Original Issue:** The model is a **binary classifier** that only answers "Is this a good BUY opportunity?"  
It has **NO concept of shorting or selling**. We were dishonestly using low buy-confidence as a "sell signal".

**This Session's Solution:** Build **honest, layered exit management**:
1. **Buy signals** from the model (what it was trained for)
2. **Exit rules** based on logic (time, stop-loss, signal decay)
3. **Sell signals** from dedicated classifier (future enhancement)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ ENTRY DECISION (Model-Based)                               │
│ ─────────────────────────────────────────────────────────── │
│ buy_conf = BUY_MODEL.predict_proba(X)[:, 1]               │
│                                                              │
│ 🟢 BUY:      buy_conf >= 0.65 (strong edge)               │
│ 🟠 MODERATE: buy_conf >= 0.55 (moderate edge)             │
│ ⚪ HOLD:     else (no edge or uncertain)                  │
│ 🔴 AVOID:    buy_conf < 0.45 (likely won't work)          │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    [User BUYS stock]
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ EXIT DECISION (Rule-Based)                                 │
│ ─────────────────────────────────────────────────────────── │
│ Apply EXIT_RULES to active positions:                       │
│                                                              │
│ ⏰ TIME-BASED: Exit after 10 days (model horizon)          │
│    → Redeploy capital, edge disappears after lookback      │
│                                                              │
│ 🛑 STOP-LOSS: Exit if price drops 5% from entry           │
│    → Limit losses, position management                     │
│                                                              │
│ 📉 SIGNAL DECAY: Exit if buy_conf < 0.45 next day        │
│    → Model says "not a good buy anymore"                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    [User EXITS position]
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ FUTURE: SELL SIGNALS (Model-Based, Phase 2)               │
│ ─────────────────────────────────────────────────────────── │
│ sell_conf = SELL_MODEL.predict_proba(X)[:, 1]             │
│                                                              │
│ 🔴 SELL:     sell_conf >= 0.65 (strong bearish)           │
│ 🟡 WEAK_SELL: sell_conf >= 0.55 (moderate bearish)        │
│                                                              │
│ (Not implemented yet - requires training new model)        │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Exit Rules Service (NOW - No Model Retraining)

**File:** `app/exit_rules.py` → `ExitRulesService` class

**Three Exit Triggers:**

### 1. Time-Based Exit (10 days)
```python
days_held = (today - entry_date).days
if days_held >= 10:
    exit("10-day horizon reached")
```
**Why?** Model trained on 10-day forward returns. After 10 days, pattern may be exhausted.

### 2. Stop-Loss Exit (5% default)
```python
stop_loss_price = entry_price * 0.95  # 5% loss
if current_price <= stop_loss_price:
    exit(f"Stop-loss hit: down {loss_pct:.1f}%")
```
**Why?** Risk management. Limits losses on failed trades.

### 3. Signal Decay Exit
```python
if current_buy_conf < 0.45:  # Confidence threshold
    exit("Buy signal weakened")
```
**Why?** Model's conviction has dropped. Edge may be gone.

**Usage Example:**
```python
from app.exit_rules import ExitRulesService

# Initialize with parameters
rules = ExitRulesService(
    exit_days=10,           # Match model horizon
    stop_loss_pct=5.0,      # Limit losses to 5%
    min_buy_conf=0.45       # Minimum buy confidence to hold
)

# Check if position should exit
exit_signal = rules.check_exit(
    entry_date=datetime(2025, 5, 1),
    entry_price=100.0,
    current_price=97.0,      # Down 3%
    current_buy_conf=0.42    # Confidence weakened
)

if exit_signal.should_exit:
    print(f"EXIT: {exit_signal.reason}")
    # → "EXIT: Buy signal weakened: confidence 0.42 < threshold 0.45"
```

**Status Display (for users):**
```python
status = rules.get_exit_status(
    entry_date, entry_price, current_price, current_buy_conf
)
# Returns:
# {
#   "days_held": 7,
#   "days_remaining": 3,
#   "stop_loss_price": 95.0,
#   "distance_to_stop_loss_pct": 2.1,
#   "current_return_pct": -3.0,
#   "buy_confidence": 0.42,
#   "risks": ["📉 Buy signal weakening (confidence: 0.42)"],
#   "should_exit_soon": True
# }
```

**Advantages:**
- ✅ No model retraining needed
- ✅ Immediate implementation
- ✅ Realistic (how actual traders exit)
- ✅ Configurable parameters
- ✅ Transparent rules

**Limitations:**
- ❌ Parameters are arbitrary (5% stop-loss, 10 days)
- ❌ Not data-driven
- ❌ Requires tuning for optimal performance

---

## Phase 2: Dedicated SELL Classifier (FUTURE - Requires Training)

**Goal:** Train a second model that predicts "Is this stock going DOWN?"

### Label Construction

**Current (BUY model):**
```python
# In src/04_label_construction.py
Label_10d_buy = (Fwd_ret_10d > +0.01).astype(int)  # 1% threshold
```

**New (SELL model - mirror logic):**
```python
Label_10d_sell = (Fwd_ret_10d < -0.01).astype(int)  # -1% threshold
```

### Model Training

**Same as BUY model:**
- Same 24 features (momentum, volatility, volume, returns, context)
- Same fold structure (7 walk-forward folds, 2012-2025)
- Same XGBoost hyperparameters
- Same StandardScaler per fold

**Output:** `model_fold{1-7}_sell.pkl` (parallel to buy models)

### Signal Logic

```python
buy_conf = buy_model.predict_proba(X)[:, 1]
sell_conf = sell_model.predict_proba(X)[:, 1]

if buy_conf >= 0.65:      # 🟢 BUY (strong bullish)
    signal = "BUY"
elif buy_conf >= 0.55:    # 🟠 MODERATE (moderate bullish)
    signal = "MODERATE"
elif sell_conf >= 0.65:   # 🔴 SELL (strong bearish)
    signal = "SELL"
elif sell_conf >= 0.55:   # 🟡 WEAK_SELL (moderate bearish)
    signal = "WEAK_SELL"
else:                     # ⚪ HOLD (neutral/uncertain)
    signal = "HOLD"
```

### Architecture Change

```python
class SignalService:
    def __init__(self, loader: DataLoader):
        self.loader = loader
        self.buy_model = loader.model      # Existing
        self.sell_model = loader.sell_model  # NEW (Phase 2)
    
    def get_verdict(self, confidence: float) -> Tuple[str, str]:
        """Return (verdict_text, color) based on buy/sell probabilities"""
        # Implementation using both models
```

**Advantages:**
- ✅ Symmetric, clean, honest
- ✅ True sell probability (not inverted buy)
- ✅ Professional, production-ready
- ✅ Data-driven (trained on historical patterns)

**Limitations:**
- ❌ Requires model retraining (~1-2 hours)
- ❌ Need to maintain two models in production
- ❌ Must update backend code after training

---

## Phase 3: Combining Both Approaches

**Most Robust:** Use BOTH exit rules AND sell classifier.

```python
def get_signal_with_exits(symbol, entry_date=None, entry_price=None):
    """
    Get signal with exit guidance.
    Combines model-based entry, rule-based exits, future sell signals.
    """
    
    # Get current prices and confidence
    buy_conf = get_buy_confidence(symbol)
    sell_conf = get_sell_confidence(symbol)  # Phase 2
    current_price = get_price(symbol)
    
    # Entry signals (from models)
    if buy_conf >= 0.65:
        entry_signal = ("BUY", "green")
    elif sell_conf >= 0.65:
        entry_signal = ("SELL", "red")
    else:
        entry_signal = ("HOLD", "gray")
    
    # Exit guidance (from rules, if holding)
    exit_guidance = None
    if entry_date:  # User has an active position
        exit_signal = exit_rules.check_exit(
            entry_date, entry_price, current_price, buy_conf
        )
        if exit_signal.should_exit:
            exit_guidance = {
                "reason": exit_signal.reason,
                "type": exit_signal.reason_type,  # "time_based", "stop_loss", "signal_decay"
                "return_pct": exit_signal.exit_return_pct
            }
    
    return {
        "entry_signal": entry_signal,
        "exit_guidance": exit_guidance,
        "buy_conf": buy_conf,
        "sell_conf": sell_conf,  # None until Phase 2
    }
```

---

## Implementation Timeline

| Phase | Component | Status | Est. Time | Dependencies |
|-------|-----------|--------|-----------|--------------|
| 1 | Exit Rules Service | ✅ DONE | - | None |
| 1 | Exit Rules → Frontend | 🔄 IN PROGRESS | 1 hour | Exit Rules done |
| 2 | Label Construction (SELL) | ⏳ PENDING | 1 hour | Codebase exploration |
| 2 | Train SELL Classifier | ⏳ PENDING | 2 hours | Label construction |
| 2 | Integrate SELL Model | ⏳ PENDING | 1 hour | SELL training done |
| 3 | Combine Both Approaches | ⏳ PENDING | 1 hour | All above done |

---

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `app/exit_rules.py` | ExitRulesService class | ✅ Created |
| `app/signal_service.py` | Load models, generate signals | 🔄 Will update for Phase 2 |
| `app/routes.py` | API endpoints | 🔄 Will add exit guidance endpoint |
| `frontend/src/components/ExitGuidance.tsx` | Show exit triggers to users | 📝 To create |
| `src/04_label_construction.py` | Create SELL labels | 📝 To modify for Phase 2 |
| `src/06_train_model.py` | Train SELL model | 📝 To modify for Phase 2 |

---

## Summary: Why This Approach is Better

| Aspect | Old Way | New Way |
|--------|---------|---------|
| **Sell Signal Source** | Inverted buy confidence ❌ | Dedicated model or rules ✅ |
| **Honesty** | Misleading (model never trained on sells) | Honest about what model does ✅ |
| **Implementation** | Fast but wrong | Right way (Phase 1 fast, Phase 2 robust) ✅ |
| **User Trust** | Undermined by wrong signals | Built through transparency ✅ |
| **Production-Ready** | No (fundamentally flawed) | Yes, with exit rules immediately ✅ |

**Result:** Retail investors get honest, actionable guidance for BOTH entry AND exit.
