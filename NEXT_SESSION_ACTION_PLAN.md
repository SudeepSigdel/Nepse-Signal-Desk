# START HERE NEXT SESSION - Action Plan

## Current State
- Exit Rules Service: ✅ DONE (working code)
- API endpoint: 🔄 NEEDS INTEGRATION
- Frontend component: 🔄 NEEDS CREATION  
- Tests: 🔄 NEEDS WRITING

## Your Exact Next Steps (Copy-Paste Ready)

### Step 1: Add API Endpoint (20 minutes)

**File:** `app/routes.py`

Add this to the end of the file:

```python
from pydantic import BaseModel
from app.exit_rules import exit_rules

class PositionCheckRequest(BaseModel):
    symbol: str
    entry_date: str  # ISO format: "2025-05-01"
    entry_price: float
    current_price: float
    current_buy_conf: float

class ExitStatusResponse(BaseModel):
    should_exit: bool
    reason: str = None
    exit_type: str = None
    days_held: int
    days_remaining: int
    current_return_pct: float
    distance_to_stop_loss_pct: float
    risks: list

@router.post("/api/positions/exit-check", response_model=ExitStatusResponse)
def check_position_exit(request: PositionCheckRequest):
    """Check if an active position should be exited."""
    from datetime import datetime
    try:
        entry_date = datetime.fromisoformat(request.entry_date)
        
        exit_signal = exit_rules.check_exit(
            entry_date=entry_date,
            entry_price=request.entry_price,
            current_price=request.current_price,
            current_buy_conf=request.current_buy_conf
        )
        
        status = exit_rules.get_exit_status(
            entry_date=entry_date,
            entry_price=request.entry_price,
            current_price=request.current_price,
            current_buy_conf=request.current_buy_conf
        )
        
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Test it:**
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

### Step 2: Create Frontend Component (30 minutes)

**File:** `frontend/src/components/PositionExitGuidance.tsx`

```tsx
import React from 'react';

interface ExitStatus {
  should_exit: boolean;
  reason?: string;
  exit_type?: 'time_based' | 'stop_loss' | 'signal_decay';
  days_held: number;
  days_remaining: number;
  current_return_pct: number;
  distance_to_stop_loss_pct: number;
  risks: string[];
}

export function PositionExitGuidance({ status }: { status: ExitStatus }) {
  if (status.should_exit) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <p className="text-red-400 font-semibold">🚨 {status.reason}</p>
        <p className="text-red-300 text-sm mt-1">Exit type: {status.exit_type?.replace('_', ' ')}</p>
      </div>
    );
  }

  return (
    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 space-y-3">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-neutral-400 text-xs">Days Held</p>
          <p className="text-white font-bold text-lg">{status.days_held} / 10</p>
          <div className="w-full bg-neutral-700 rounded h-1 mt-1">
            <div 
              className="bg-blue-500 h-1 rounded" 
              style={{ width: `${(status.days_held / 10) * 100}%` }}
            />
          </div>
        </div>
        
        <div>
          <p className="text-neutral-400 text-xs">Current Return</p>
          <p className={`font-bold text-lg ${status.current_return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {status.current_return_pct > 0 ? '+' : ''}{status.current_return_pct.toFixed(1)}%
          </p>
        </div>
        
        <div>
          <p className="text-neutral-400 text-xs">Stop-Loss Distance</p>
          <p className="text-white font-bold text-lg">{status.distance_to_stop_loss_pct.toFixed(1)}%</p>
        </div>
        
        <div>
          <p className="text-neutral-400 text-xs">Days Remaining</p>
          <p className="text-white font-bold text-lg">{status.days_remaining}</p>
        </div>
      </div>

      {status.risks.length > 0 && (
        <div>
          <p className="text-xs text-neutral-400 mb-2 font-semibold">Active Risks:</p>
          <div className="space-y-1">
            {status.risks.map((risk, idx) => (
              <p key={idx} className="text-xs text-neutral-300">• {risk}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

### Step 3: Integrate into Detail Page (10 minutes)

**File:** `frontend/src/pages/StockDetailPage.tsx`

Add this to the component:

```tsx
import { PositionExitGuidance } from '../components/PositionExitGuidance';

// Inside your component:
const [exitStatus, setExitStatus] = useState<ExitStatus | null>(null);
const [userEntryDate, setUserEntryDate] = useState('');
const [userEntryPrice, setUserEntryPrice] = useState<number>(0);

useEffect(() => {
  if (userEntryDate && userEntryPrice) {
    fetch('/api/positions/exit-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol,
        entry_date: userEntryDate,
        entry_price: userEntryPrice,
        current_price,
        current_buy_conf: confidence
      })
    }).then(r => r.json()).then(setExitStatus).catch(console.error);
  }
}, [symbol, userEntryDate, userEntryPrice, current_price, confidence]);

// In render:
return (
  <div className="space-y-6">
    <SignalCard {...signalData} />
    
    {/* User input for entry point */}
    <div className="bg-neutral-900/50 border border-neutral-700/50 rounded-lg p-4 space-y-2">
      <h3 className="text-white font-semibold text-sm">Your Position (Optional)</h3>
      <div className="grid grid-cols-2 gap-2">
        <input 
          type="date" 
          value={userEntryDate}
          onChange={(e) => setUserEntryDate(e.target.value)}
          className="bg-neutral-800 text-white text-sm p-2 rounded"
        />
        <input 
          type="number" 
          placeholder="Entry price"
          value={userEntryPrice || ''}
          onChange={(e) => setUserEntryPrice(parseFloat(e.target.value) || 0)}
          className="bg-neutral-800 text-white text-sm p-2 rounded"
        />
      </div>
    </div>
    
    {/* Exit guidance if position entered */}
    {exitStatus && <PositionExitGuidance status={exitStatus} />}
  </div>
);
```

### Step 4: Write Tests (30 minutes)

**File:** `tests/test_exit_rules_integration.py`

```python
import pytest
from datetime import datetime, timedelta
from app.exit_rules import ExitRulesService

@pytest.fixture
def rules():
    return ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)

def test_time_based_exit(rules):
    entry = datetime.now() - timedelta(days=10)
    signal = rules.check_exit(entry, 100.0, 100.0, 0.7)
    assert signal.should_exit == True
    assert signal.reason_type == "time_based"

def test_stop_loss_exit(rules):
    signal = rules.check_exit(datetime.now(), 100.0, 94.5, 0.7)
    assert signal.should_exit == True
    assert signal.reason_type == "stop_loss"

def test_signal_decay_exit(rules):
    signal = rules.check_exit(datetime.now(), 100.0, 105.0, 0.40)
    assert signal.should_exit == True
    assert signal.reason_type == "signal_decay"

def test_no_exit_needed(rules):
    signal = rules.check_exit(datetime.now() - timedelta(days=5), 100.0, 105.0, 0.70)
    assert signal.should_exit == False

def test_exit_status_structure(rules):
    status = rules.get_exit_status(datetime.now() - timedelta(days=5), 100.0, 103.0, 0.68)
    assert 'days_held' in status
    assert 'days_remaining' in status
    assert 'current_return_pct' in status
    assert 'distance_to_stop_loss_pct' in status
    assert 'risks' in status
```

**Run tests:**
```bash
pytest tests/test_exit_rules_integration.py -v
```

---

## Verification Checklist

- [ ] Exit rules service file exists: `app/exit_rules.py`
- [ ] Endpoint added to `app/routes.py`
- [ ] Frontend component created: `PositionExitGuidance.tsx`
- [ ] Integrated into StockDetailPage
- [ ] API responds to `/api/positions/exit-check`
- [ ] Test curl command works
- [ ] Frontend renders without errors
- [ ] All three exit triggers tested
- [ ] Stop-loss calculation correct
- [ ] Days remaining shows accurately
- [ ] Risks display properly

---

## Time Estimate
- API endpoint: 20 min
- Frontend component: 30 min
- Integration: 10 min
- Testing: 30 min
- **Total: ~90 minutes (1.5 hours)**

---

## Common Issues & Quick Fixes

**Issue:** "Cannot import exit_rules"
**Fix:** Make sure `app/exit_rules.py` exists and is in the right directory

**Issue:** API returns 400 Bad Request
**Fix:** Check date format (ISO: "2025-05-01") in your curl/request

**Issue:** Component doesn't display
**Fix:** Import it: `import { PositionExitGuidance } from '../components/PositionExitGuidance';`

**Issue:** Tests fail
**Fix:** Run `pytest --tb=short` for detailed error messages

---

## What You're Completing

✅ Phase 1: Exit Rules Integration
  - API endpoint working
  - Frontend component showing exit guidance
  - Tests passing
  - Users can see when to exit positions

After this: Phase 2 (Train SELL classifier) and Phase 3 (Combine all layers)

---

## Documentation Reference

If you get stuck:
1. `QUICK_REFERENCE.md` — Examples and patterns
2. `EXIT_RULES_INTEGRATION.py` — Detailed code examples
3. `app/exit_rules.py` — Source code (read the ExitSignal class)
4. `PHASE_3_CHECKLIST.md` — All tasks and acceptance criteria

Good luck! The hardest part (designing the architecture) is done. ✅
