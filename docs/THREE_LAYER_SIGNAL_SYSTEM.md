# Honest Signal Architecture - Visual Summary

## Three-Layer Signal System

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        SIGNAL GENERATION SYSTEM                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

LAYER 1: ENTRY SIGNAL (What we predict will go UP/DOWN)
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  Input: Current price, technicals, volume, momentum                          │
│         ↓                                                                    │
│  [BUY_MODEL]  Outputs: P(buy opportunity) ∈ [0, 1]                         │
│         ↓                                                                    │
│  VERDICT:                                                                    │
│  • 🟢 BUY        (conf ≥ 0.65) → Strong bullish pattern                     │
│  • 🟠 MODERATE   (conf ≥ 0.55) → Moderate bullish pattern                  │
│  • ⚪ HOLD       (else)        → Neutral/no edge                            │
│                                                                              │
│  [SELL_MODEL]  Outputs: P(sell opportunity) ∈ [0, 1]  [Phase 2]           │
│         ↓                                                                    │
│  VERDICT:                                                                    │
│  • 🔴 SELL       (conf ≥ 0.65) → Strong bearish pattern                    │
│  • 🟡 WEAK_SELL  (conf ≥ 0.55) → Moderate bearish pattern                 │
│                                                                              │
│  Both models always score. You ACT on highest conviction:                    │
│  IF buy_conf >= 0.65 AND sell_conf < 0.55 → BUY                            │
│  IF sell_conf >= 0.65 AND buy_conf < 0.55 → SELL                           │
│  IF both moderate/high → HOLD (conflicting signals)                         │
│  IF both low → HOLD (no edge)                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                            [User ENTERS position]
                                     ↓
LAYER 2: EXIT RULES (When to take profits/cut losses)
┌─────────────────────────────────────────────────────────────────────────────┐
│ For every ACTIVE position, check three exit triggers:                        │
│                                                                              │
│ 1. ⏰ TIME-BASED                                                             │
│    Entry: May 1    Days held: 10    → EXIT                                  │
│    Entry: May 1    Days held: 7     → HOLD (3 days remaining)              │
│    WHY: Model trained on 10-day forward returns. After 10d, edge exhausted  │
│                                                                              │
│ 2. 🛑 STOP-LOSS (5% loss limit)                                             │
│    Entry: $100     Current: $95     → EXIT (5% loss)                       │
│    Entry: $100     Current: $97     → HOLD (3% loss, 2% buffer)            │
│    WHY: Risk management. Prevent large losses on failed signals             │
│                                                                              │
│ 3. 📉 SIGNAL DECAY (confidence drops)                                        │
│    Entry confidence: 0.70 → Today: 0.42  → EXIT (below 0.45)              │
│    Entry confidence: 0.70 → Today: 0.48  → HOLD (above 0.45)              │
│    WHY: Model's conviction weakened. Pattern may have changed               │
│                                                                              │
│ Display to user:                                                             │
│ "Days held: 7/10 | Return: -3% | Risk: Signal decaying (0.42) ⚠️"         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
                            [User EXITS position]
                                     ↓
LAYER 3: SELL SIGNALS (Future true SHORT signals)  [Phase 2]
┌─────────────────────────────────────────────────────────────────────────────┐
│ Separate model trained to predict DOWNSIDE                                  │
│ Used as standalone signal (not just exit condition)                         │
│                                                                              │
│ Currently NOT implemented (would require:                                   │
│  - Retraining on downside labels)                                           │
│  - Publishing two models to production                                      │
│  - More monitoring)                                                          │
│                                                                              │
│ When ready, can be combined with exit rules for maximum control             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Single API Call

```
User asks: "What should I do with AAPL?"

POST /api/stocks/AAPL/signal
{
  "symbol": "AAPL",
  "entry_date": "2025-05-01",        // Optional: user's entry point
  "entry_price": 180.50               // Optional: user's entry price
}

┌──────────────────────────────────────────────────────────────────┐
│ Backend Processing:                                               │
│                                                                  │
│ 1. Load current price, technicals                               │
│ 2. Run through buy_model → buy_conf = 0.68                     │
│ 3. Run through sell_model → sell_conf = 0.22                   │
│ 4. Determine entry verdict:                                     │
│    buy_conf (0.68) > sell_conf (0.22)                          │
│    buy_conf ≥ 0.65 → "BUY"                                     │
│                                                                  │
│ 5. IF user has active position:                                │
│    - Check time-based: 5 days held < 10 ✓                      │
│    - Check stop-loss: 3% down > -5% ✓                          │
│    - Check signal decay: conf 0.68 > 0.45 ✓                    │
│    - Result: "HOLD position, 5 days remaining"                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

Response:
{
  "symbol": "AAPL",
  "entry": {
    "verdict": "BUY",
    "color": "green",
    "buy_confidence": 0.68,
    "sell_confidence": 0.22,
    "description": "Strong bullish pattern detected. Model found similar patterns that gained 8% in 10 days."
  },
  "position": {                          // Only if user provided entry_date/price
    "days_held": 5,
    "days_remaining": 5,
    "current_return": 2.5,
    "stop_loss_price": 171.48,
    "distance_to_stop_loss": 1.5,
    "risks": [],
    "should_exit": false,
    "exit_reason": null
  },
  "actions": {
    "if_no_position": "Buy 10-20 shares. Set stop-loss at $171. Plan to exit in 10 days.",
    "if_holding": "Hold for 5 more days unless stop-loss hit.",
    "if_warning": null
  }
}
```

---

## Component Integration

```
┌─────────────────────────────────────┐
│      DashboardOverview.tsx           │
│  ┌──────────────────────────────┐   │
│  │ [? Glossary] [Risk Warnings] │   │
│  │                              │   │
│  │ Stocks Table:                │   │
│  │ AAPL │ 🟢 BUY  │ 0.68       │   │
│  │      │ Exit: 5d │ $171 SL   │   │
│  │      │ Return: +2.5%        │   │
│  └──────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
                   ↓ Click AAPL
┌─────────────────────────────────────┐
│      StockDetailPage.tsx             │
│  ┌──────────────────────────────┐   │
│  │ SignalCard:                  │   │
│  │  🟢 BUY (68%)                │   │
│  │  "Strong pattern"            │   │
│  │  [Buy] [Risk] [Learn More]   │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ PositionExitGuidance:        │   │
│  │  Days: 5/10                  │   │
│  │  Return: +2.5%               │   │
│  │  Stop-Loss: $171.48          │   │
│  │  ⚠️ Risks: None              │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │ CompanyInfo:                 │   │
│  │  Sector: Technology          │   │
│  │  Market Cap: $2.8T           │   │
│  │  52-Week: $165-$195          │   │
│  └──────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
```

---

## Truth Table: When to BUY/SELL/HOLD

```
Buy Conf | Sell Conf | Verdict | Reason
---------|-----------|---------|------------------------------------------------
 ≥ 0.65  |  < 0.55   | 🟢 BUY  | Strong bullish, no bearish conflict
 ≥ 0.55  |  < 0.55   | 🟠 MOD  | Moderate bullish, no bearish conflict
 < 0.55  |  ≥ 0.65   | 🔴 SELL | Strong bearish, no bullish conflict
 < 0.55  |  ≥ 0.55   | 🟡 WSELL| Moderate bearish, no bullish conflict
 < 0.55  |  < 0.55   | ⚪ HOLD  | No edge, both models uncertain
 ≥ 0.65  |  ≥ 0.55   | ⚪ HOLD  | Conflicting signals, wait for clarity
 ≥ 0.55  |  ≥ 0.65   | ⚪ HOLD  | Conflicting signals, wait for clarity
 ≥ 0.45  |  ≥ 0.45   | ⚪ HOLD  | Both marginal, no clear edge

Rule: ACT only when one model has clear conviction AND other doesn't conflict
```

---

## Why This Approach Works

| Aspect | Old Way ❌ | New Way ✅ |
|--------|-----------|-----------|
| **Sell Signal** | Use low buy_conf | Train separate model |
| **Honesty** | Misleading (not trained for sells) | Transparent about what each model does |
| **Entry Rules** | Only BUY, no SELL | Model predicts both directions |
| **Exit Rules** | No guidance | Time/stop-loss/decay |
| **Risk Mgmt** | Random | Systematic (stop-loss, time horizon) |
| **User Trust** | Low (wrong signals) | High (multiple confirmation layers) |
| **Production** | Risky | Robust (three layers of defense) |

---

## Implementation Phases

```
NOW (Phase 1)          NEXT (Phase 2)         LATER (Phase 3)
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Exit Rules      │    │ SELL Classifier │    │ Combined UI     │
│ (Logic-based)   │    │ (Model-based)   │    │ (All 3 layers)  │
│                 │    │                 │    │                 │
│ • Time-based ✓  │    │ • Train SELL ✓  │    │ • Dashboard ✓   │
│ • Stop-loss ✓   │    │ • Load models ✓ │    │ • Detail page ✓ │
│ • Signal decay ✓│    │ • 5-way verdict │    │ • Docs ✓        │
│                 │    │   (BUY/MOD/SELL)│    │ • Backtests ✓   │
│ 4 hours work    │    │                 │    │                 │
│ ~ 2-3 features │    │ 3 hours work     │    │ 2 hours work    │
│                 │    │ ~ 24 features × 2│   │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## Key Insight

The model **answers ONE question:** "Will this stock go UP?"

But traders need **THREE answers:**
1. **ENTER?** Model says yes → Go long
2. **HOLD?** Exit rules say no early/stop-loss/decay → Exit
3. **SHORT?** (Future) Separate model says yes → Go short

By separating these concerns, we're **honest, systematic, and professional**.
