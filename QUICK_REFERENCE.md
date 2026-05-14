# Quick Reference: Exit Rules + Sell Classifier

## What We Built

### ✅ Exit Rules Service (DONE)
```python
from app.exit_rules import ExitRulesService

rules = ExitRulesService(
    exit_days=10,
    stop_loss_pct=5.0,
    min_buy_conf=0.45
)

# Check if position should exit
signal = rules.check_exit(
    entry_date=datetime(2025, 5, 1),
    entry_price=100.0,
    current_price=95.0,
    current_buy_conf=0.42
)

if signal.should_exit:
    print(f"EXIT: {signal.reason}")
    # → "EXIT: Stop-loss triggered: -5.0%"
```

---

## Next Steps (Ordered by Priority)

### PRIORITY 1: Exit Rules API (1 hour)
**Goal:** Expose exit rules to frontend via API

```python
# app/routes.py - Add this endpoint:
@router.post("/api/positions/exit-check")
def check_position_exit(request: PositionCheckRequest):
    entry_date = datetime.fromisoformat(request.entry_date)
    exit_signal = exit_rules.check_exit(
        entry_date=entry_date,
        entry_price=request.entry_price,
        current_price=request.current_price,
        current_buy_conf=request.current_buy_conf
    )
    
    status = exit_rules.get_exit_status(...)
    return ExitStatusResponse(
        should_exit=exit_signal.should_exit,
        reason=exit_signal.reason,
        exit_type=exit_signal.reason_type,
        days_held=exit_signal.days_held,
        days_remaining=max(0, 10 - exit_signal.days_held),
        current_return_pct=exit_signal.exit_return_pct,
        distance_to_stop_loss_pct=status['distance_to_stop_loss_pct'],
        risks=status['risks']
    )
```

**Test:**
```bash
curl -X POST http://localhost:8000/api/positions/exit-check \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "entry_date": "2025-05-01",
    "entry_price": 180.50,
    "current_price": 178.25,
    "current_buy_conf": 0.68
  }'
```

---

### PRIORITY 2: Exit Guidance Component (1 hour)
**Goal:** Display exit guidance on detail page

```tsx
// frontend/src/components/PositionExitGuidance.tsx
export function PositionExitGuidance({ status }: { status: ExitStatus }) {
  const riskLevel = status.days_held / 10;
  const stopLossRisk = (1 - (status.distance_to_stop_loss_pct / 100));
  
  return (
    <div className="space-y-4">
      {/* Time-based exit warning */}
      {status.days_remaining <= 2 && (
        <div className="bg-orange-500/10 border border-orange-500/30 rounded p-3">
          <p className="text-orange-400 text-sm">
            ⏰ Approaching 10-day exit ({status.days_remaining}d left)
          </p>
        </div>
      )}

      {/* Stop-loss warning */}
      {stopLossRisk > 0.7 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
          <p className="text-red-400 text-sm">
            🛑 Stop-loss close: {status.distance_to_stop_loss_pct.toFixed(1)}% buffer
          </p>
        </div>
      )}

      {/* Signal decay warning */}
      {status.risks.some(r => r.includes('Signal')) && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3">
          <p className="text-yellow-400 text-sm">
            📉 Signal weakening: confidence {status.buy_confidence.toFixed(2)}
          </p>
        </div>
      )}

      {/* Exit button if should_exit */}
      {status.should_exit && (
        <button className="w-full bg-red-600 hover:bg-red-700 p-2 rounded text-white">
          🚨 EXIT NOW: {status.reason}
        </button>
      )}
    </div>
  );
}
```

**Usage:**
```tsx
// frontend/src/pages/StockDetailPage.tsx
const [exitStatus, setExitStatus] = useState<ExitStatus | null>(null);

useEffect(() => {
  if (userEntryDate && userEntryPrice) {
    fetch('/api/positions/exit-check', {
      method: 'POST',
      body: JSON.stringify({
        symbol,
        entry_date: userEntryDate,
        entry_price: userEntryPrice,
        current_price,
        current_buy_conf: confidence
      })
    }).then(r => r.json()).then(setExitStatus);
  }
}, [symbol, userEntryDate, userEntryPrice, current_price, confidence]);

return (
  <div>
    <SignalCard {...signalData} />
    {exitStatus && <PositionExitGuidance status={exitStatus} />}
  </div>
);
```

---

### PRIORITY 3: Testing (1 hour)
**Goal:** Ensure exit rules work correctly

```python
# tests/test_exit_rules.py
def test_time_based_exit():
    rules = ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)
    entry = datetime.now() - timedelta(days=10)
    signal = rules.check_exit(entry, 100.0, 100.0, 0.7)
    assert signal.should_exit == True
    assert signal.reason_type == "time_based"

def test_stop_loss_exit():
    rules = ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)
    signal = rules.check_exit(datetime.now(), 100.0, 94.5, 0.7)
    assert signal.should_exit == True
    assert signal.reason_type == "stop_loss"

def test_signal_decay_exit():
    rules = ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)
    signal = rules.check_exit(datetime.now(), 100.0, 105.0, 0.40)
    assert signal.should_exit == True
    assert signal.reason_type == "signal_decay"

def test_no_exit():
    rules = ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)
    signal = rules.check_exit(datetime.now() - timedelta(days=5), 100.0, 105.0, 0.70)
    assert signal.should_exit == False

def test_api_endpoint():
    client = TestClient(app)
    response = client.post("/api/positions/exit-check", json={
        "symbol": "AAPL",
        "entry_date": "2025-05-01",
        "entry_price": 100.0,
        "current_price": 97.0,
        "current_buy_conf": 0.42
    })
    assert response.status_code == 200
    assert response.json()["should_exit"] == True
```

**Run:**
```bash
pytest tests/test_exit_rules.py -v
```

---

## LATER: Sell Classifier (3 hours - Next Session)

### Phase 2a: Update Labels
```python
# src/04_label_construction.py - ADD THIS:
Label_10d_sell = (Fwd_ret_10d < -0.01).astype(int)  # Mirror logic
```

### Phase 2b: Train Model
```python
# src/06_train_model.py - ADD THIS:
# Same training as buy model, but on Label_10d_sell
for fold in range(7):
    X_train, y_train = get_fold_data(fold)
    y_sell = y_train_sell[fold]  # NEW: sell labels
    
    model = xgb.XGBClassifier(...)
    model.fit(X_train, y_sell)  # Fit on sell labels
    joblib.dump(model, f'models/model_fold{fold}_sell.pkl')  # NEW filename
```

### Phase 2c: Load Both Models
```python
# app/data_loader.py - MODIFY:
class DataLoader:
    def __init__(self):
        self.buy_models = [
            joblib.load(f'models/model_fold{i}_buy.pkl') for i in range(7)
        ]
        self.sell_models = [  # NEW
            joblib.load(f'models/model_fold{i}_sell.pkl') for i in range(7)
        ]
```

### Phase 2d: Update Signal Logic
```python
# app/signal_service.py - MODIFY:
def get_verdict(self, buy_conf, sell_conf):
    if buy_conf >= 0.65 and sell_conf < 0.55:
        return "BUY", "green"
    elif buy_conf >= 0.55 and sell_conf < 0.55:
        return "MODERATE", "orange"
    elif sell_conf >= 0.65 and buy_conf < 0.55:
        return "SELL", "red"
    elif sell_conf >= 0.55 and buy_conf < 0.55:
        return "WEAK_SELL", "orange-red"
    else:
        return "HOLD", "gray"
```

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| `should_exit` always False | Not checking current_buy_conf | Ensure current_buy_conf < 0.45 for decay test |
| Stop-loss never triggers | Using > instead of <= | Check comparison: `current_price <= stop_loss_price` |
| Days calculation wrong | Not using datetime.now() | Use `datetime.now()` or pass explicit `current_date` |
| API returns 500 | Missing ExitStatus schema | Add to `app/schemas.py` |
| Frontend can't find endpoint | Routes not imported | Ensure `app/routes.py` imported in `app/main.py` |

---

## Success Checklist

- [ ] Exit rules service exists in `app/exit_rules.py`
- [ ] API endpoint `/api/positions/exit-check` works
- [ ] `PositionExitGuidance` component displays correctly
- [ ] All three exit triggers tested
- [ ] Frontend shows exit guidance without errors
- [ ] Stop-loss percentage configurable
- [ ] Users can see days remaining until 10-day exit
- [ ] Can test with historical data
- [ ] Documentation complete and clear
- [ ] Retail investor understands "why exit"

---

## Files Reference

| File | Purpose | Status |
|------|---------|--------|
| `app/exit_rules.py` | Exit logic | ✅ |
| `app/routes.py` | API endpoint | 🔄 |
| `app/schemas.py` | Response schema | 🔄 |
| `frontend/src/components/PositionExitGuidance.tsx` | Display | 🔄 |
| `docs/HONEST_SIGNAL_ARCHITECTURE.md` | Full reference | ✅ |
| `docs/THREE_LAYER_SIGNAL_SYSTEM.md` | Visual guide | ✅ |
| `PHASE_3_CHECKLIST.md` | All tasks | ✅ |

---

## Questions?

Refer to:
- `EXIT_RULES_INTEGRATION.py` — Implementation examples
- `HONEST_SIGNAL_ARCHITECTURE.md` — Design philosophy
- `THREE_LAYER_SIGNAL_SYSTEM.md` — Visual architecture
- Existing `app/exit_rules.py` — Source code reference
