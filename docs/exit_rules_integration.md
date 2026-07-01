# Exit Rules Integration Guide

How `ExitRulesService` (`app/services/exit_rules.py`) is used across the codebase.

## Basic usage

```python
from app.services.exit_rules import ExitRulesService
from datetime import datetime

exit_rules = ExitRulesService(
    exit_days=10,           # Time horizon (matches model)
    stop_loss_pct=5.0,      # 5% loss limit
    min_buy_conf=0.45       # Minimum confidence to hold
)

exit_signal = exit_rules.check_exit(
    entry_date=datetime(2025, 5, 1),
    entry_price=100.0,
    current_price=97.0,
    current_buy_conf=0.42,
    current_date=datetime(2025, 5, 5),
)

if exit_signal.should_exit:
    print(f"EXIT: {exit_signal.reason} ({exit_signal.reason_type})")
```

## Getting exit status for display

```python
status = exit_rules.get_exit_status(
    entry_date=entry_date,
    entry_price=entry_price,
    current_price=current_price,
    current_buy_conf=current_buy_conf,
)
# status: days_held, days_remaining, distance_to_stop_loss_pct,
# current_return_pct, buy_confidence, risks, should_exit_soon
```

## API endpoint

The live endpoint is `app/api/routes/positions.py` — `POST /api/positions/exit-check`,
backed by `ExitRulesService` via `app.state.exit_rules_service` (see `app/api/deps.py`).

```
POST /api/positions/exit-check
{
    "symbol": "NEPSE",
    "entry_date": "2025-05-01",
    "entry_price": 100.0,
    "current_price": 97.0,
    "current_buy_conf": 0.42
}
```

## Frontend display

`ExitStatus` (`frontend/src/types.ts`, named `ExitStatusResponse`) mirrors the backend response 1:1:

```ts
interface ExitStatusResponse {
  should_exit: boolean;
  reason: string | null;
  exit_type: 'time_based' | 'stop_loss' | 'signal_decay' | null;
  days_held: number;
  days_remaining: number;
  current_return_pct: number;
  distance_to_stop_loss_pct: number;
  risks: string[];
}
```

Two consumers render it:

- `frontend/src/components/stock/PositionHelper.tsx` — on the stock detail page. Takes an entry date/price form, calls the `useExitCheck` hook (`frontend/src/hooks/useExitCheck.ts`), and renders the result inline.
- `frontend/src/pages/PortfolioPage.tsx` + `frontend/src/hooks/useHoldingsExitStatus.ts` — checks exit status for every tracked holding in the portfolio at once.

## Custom exit rules configuration

```python
# Aggressive traders (tighter stops)
aggressive_rules = ExitRulesService(exit_days=5, stop_loss_pct=2.0, min_buy_conf=0.50)

# Conservative traders (wider stops)
conservative_rules = ExitRulesService(exit_days=15, stop_loss_pct=10.0, min_buy_conf=0.40)

# Mean-reversion traders (signal decay focused)
mean_reversion_rules = ExitRulesService(exit_days=30, stop_loss_pct=15.0, min_buy_conf=0.35)
```

Automated tests for this logic live in `tests/test_exit_rules.py`.
