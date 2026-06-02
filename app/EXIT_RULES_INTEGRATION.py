"""
Exit Rules Integration Guide
=============================

How to integrate ExitRulesService into the signal pipeline.
"""

# EXAMPLE 1: Basic Usage
# ═════════════════════════════════════════════════════════════════════════════

from app.exit_rules import ExitRulesService
from datetime import datetime, timedelta

# Initialize with default rules
exit_rules = ExitRulesService(
    exit_days=10,           # Time horizon (matches model)
    stop_loss_pct=5.0,      # 5% loss limit
    min_buy_conf=0.45       # Minimum confidence to hold
)

# Check if a position should exit
entry = {
    "symbol": "AAPL",
    "entry_date": datetime(2025, 5, 1),
    "entry_price": 100.0
}

current = {
    "current_price": 97.0,  # Down 3%
    "current_buy_conf": 0.42,
    "current_date": datetime(2025, 5, 5)  # 4 days held
}

exit_signal = exit_rules.check_exit(
    entry_date=entry["entry_date"],
    entry_price=entry["entry_price"],
    current_price=current["current_price"],
    current_buy_conf=current["current_buy_conf"],
    current_date=current["current_date"]
)

if exit_signal.should_exit:
    print(f"🚨 EXIT: {exit_signal.reason}")
    print(f"   Type: {exit_signal.reason_type}")
    print(f"   Return: {exit_signal.exit_return_pct:.1f}%")
else:
    print(f"✓ Position held. Days: {exit_signal.days_held}, Return: {exit_signal.exit_return_pct:.1f}%")


# EXAMPLE 2: Getting Exit Status for Display
# ═════════════════════════════════════════════════════════════════════════════

status = exit_rules.get_exit_status(
    entry_date=entry["entry_date"],
    entry_price=entry["entry_price"],
    current_price=current["current_price"],
    current_buy_conf=current["current_buy_conf"]
)

print("Position Status:")
print(f"  Days Held: {status['days_held']}/{exit_rules.exit_days}")
print(f"  Return: {status['current_return_pct']:.2f}%")
print(f"  Confidence: {status['buy_confidence']:.2f}")
print(f"  Stop-Loss Distance: {status['distance_to_stop_loss_pct']:.1f}%")

if status['risks']:
    print("  Active Risks:")
    for risk in status['risks']:
        print(f"    {risk}")


# EXAMPLE 3: API Endpoint Integration
# ═════════════════════════════════════════════════════════════════════════════

# In app/routes.py, add a new endpoint:

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

exit_rules_router = APIRouter()

class PositionCheckRequest(BaseModel):
    """Request to check if a position should exit."""
    symbol: str
    entry_date: str  # ISO format: "2025-05-01"
    entry_price: float
    current_price: float
    current_buy_conf: float

class ExitStatusResponse(BaseModel):
    """Response with exit status and guidance."""
    should_exit: bool
    reason: str = None
    exit_type: str = None  # "time_based", "stop_loss", "signal_decay"
    days_held: int
    days_remaining: int
    current_return_pct: float
    distance_to_stop_loss_pct: float
    risks: list

@exit_rules_router.post("/api/positions/exit-check", response_model=ExitStatusResponse)
def check_position_exit(request: PositionCheckRequest):
    """
    Check if an active position should be exited.
    
    Example request:
    POST /api/positions/exit-check
    {
        "symbol": "NEPSE",
        "entry_date": "2025-05-01",
        "entry_price": 100.0,
        "current_price": 97.0,
        "current_buy_conf": 0.42
    }
    """
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
        logger.error(f"Error checking position exit: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# EXAMPLE 4: Frontend Display Component
# ═════════════════════════════════════════════════════════════════════════════

# In frontend/src/components/PositionExitGuidance.tsx:
"""
This component shows exit guidance for positions the user is holding.

TypeScript example:
```tsx
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
        <p className="text-red-300 text-sm mt-1">Exit type: {status.exit_type}</p>
      </div>
    );
  }

  return (
    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4 space-y-3">
      <div className="flex justify-between">
        <span className="text-neutral-300">Days Held</span>
        <span className="text-white font-medium">{status.days_held} / 10</span>
      </div>
      
      <div className="flex justify-between">
        <span className="text-neutral-300">Current Return</span>
        <span className={`font-medium ${status.current_return_pct > 0 ? 'text-green-400' : 'text-red-400'}`}>
          {status.current_return_pct > 0 ? '+' : ''}{status.current_return_pct.toFixed(1)}%
        </span>
      </div>
      
      <div className="flex justify-between">
        <span className="text-neutral-300">Stop-Loss Distance</span>
        <span className="text-white font-medium">{status.distance_to_stop_loss_pct.toFixed(1)}%</span>
      </div>

      {status.risks.length > 0 && (
        <div>
          <p className="text-xs text-neutral-400 mb-2">Active Risks:</p>
          <div className="space-y-1">
            {status.risks.map((risk, idx) => (
              <p key={idx} className="text-xs text-neutral-300">{risk}</p>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```
"""


# EXAMPLE 5: Custom Exit Rules Configuration
# ═════════════════════════════════════════════════════════════════════════════

# For aggressive traders (tighter stops):
aggressive_rules = ExitRulesService(
    exit_days=5,           # Exit sooner
    stop_loss_pct=2.0,     # Tight stop-loss
    min_buy_conf=0.50      # Exit early if confidence drops
)

# For conservative traders (wider stops):
conservative_rules = ExitRulesService(
    exit_days=15,          # Give it more time
    stop_loss_pct=10.0,    # Wide stop-loss
    min_buy_conf=0.40      # Hold even if confidence drops slightly
)

# For mean-reversion traders (signal decay focused):
mean_reversion_rules = ExitRulesService(
    exit_days=30,          # Hold longer
    stop_loss_pct=15.0,    # Wide stops (capture reversals)
    min_buy_conf=0.35      # Signal decay is main exit
)


# EXAMPLE 6: Testing Exit Rules
# ═════════════════════════════════════════════════════════════════════════════

import pytest

def test_exit_rules():
    rules = ExitRulesService(exit_days=10, stop_loss_pct=5.0, min_buy_conf=0.45)
    
    # Test 1: Time-based exit
    entry_date = datetime.now() - timedelta(days=10)
    exit_signal = rules.check_exit(entry_date, 100.0, 100.0, 0.7)
    assert exit_signal.should_exit == True
    assert exit_signal.reason_type == "time_based"
    
    # Test 2: Stop-loss exit
    exit_signal = rules.check_exit(datetime.now(), 100.0, 94.5, 0.7)
    assert exit_signal.should_exit == True
    assert exit_signal.reason_type == "stop_loss"
    
    # Test 3: Signal decay exit
    exit_signal = rules.check_exit(datetime.now(), 100.0, 105.0, 0.40)
    assert exit_signal.should_exit == True
    assert exit_signal.reason_type == "signal_decay"
    
    # Test 4: No exit needed
    exit_signal = rules.check_exit(datetime.now() - timedelta(days=5), 100.0, 105.0, 0.70)
    assert exit_signal.should_exit == False

if __name__ == "__main__":
    test_exit_rules()
    print("✓ All exit rules tests passed!")
