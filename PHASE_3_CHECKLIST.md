# IMPLEMENTATION CHECKLIST: Exit Rules + Sell Classifier

## Phase 1: Exit Rules Integration (IMMEDIATE)

### ✅ 1.1 Exit Rules Service
- [x] Created `app/exit_rules.py` with ExitRulesService class
- [x] Implemented three exit triggers: time-based, stop-loss, signal decay
- [x] ExitSignal class for clean response structure
- [x] get_exit_status() for UI display

### 🔄 1.2 Backend Integration
- [ ] Add `exit_rules` instance to `app/main.py`
- [ ] Create `POST /api/positions/exit-check` endpoint
- [ ] Update StockResponse schema to include exit guidance
- [ ] Add exit_status to signal response

### 🔄 1.3 Frontend Display
- [ ] Create `frontend/src/components/PositionExitGuidance.tsx`
- [ ] Show days remaining, return %, stop-loss distance
- [ ] Display active risks
- [ ] Show exit warning if should_exit=true
- [ ] Integrate into StockDetailPage

### 🔄 1.4 Testing
- [ ] Unit test ExitRulesService (time, stop-loss, signal decay)
- [ ] Integration test API endpoint
- [ ] E2E test frontend display
- [ ] Test with realistic scenarios (3 day hold, 5% down, conf 0.42)

---

## Phase 2: Sell Classifier Training (NEXT SESSION)

### 📝 2.1 Data Preparation
- [ ] Read `src/04_label_construction.py` to understand current label logic
- [ ] Create Label_10d_sell using mirror threshold (Fwd_ret_10d < -0.01)
- [ ] Ensure 24 features match buy model
- [ ] Verify fold splits align with buy model

### 📝 2.2 Model Training
- [ ] Modify `src/06_train_model.py` to train SELL classifier
- [ ] Same hyperparameters as buy model (300 trees, max_depth=4, etc.)
- [ ] Generate 7 models: `model_fold{1-7}_sell.pkl`
- [ ] Save to same directory as buy models
- [ ] Document training time, memory usage, cross-validation scores

### 📝 2.3 Backend Integration
- [ ] Update DataLoader to load both buy and sell models
- [ ] Add sell_model property to DataLoader
- [ ] Update SignalService to compute both buy_conf and sell_conf
- [ ] Implement new verdict logic (buy/moderate/sell/weak_sell/hold)
- [ ] Update response schema with sell_conf field

### 📝 2.4 Testing
- [ ] Unit test dual-model logic
- [ ] Verify sell signals make business sense (use historical data)
- [ ] Check agreement between models (both should rarely fire together)
- [ ] Backtest: SELL signals on dates right before actual down days

---

## Phase 3: Frontend for Sell Signals

### 📝 3.1 Components
- [ ] Update `SignalCard.tsx` to show 5 verdicts (BUY, MODERATE, SELL, WEAK_SELL, HOLD)
- [ ] Add new colors for sell (red), weak_sell (orange-red)
- [ ] Update descriptions to explain sell signals vs exit rules

### 📝 3.2 Dashboard
- [ ] Show sell signals in table (red row if sell)
- [ ] Separate column for sell_confidence
- [ ] Add tooltip explaining SELL vs AVOID

### 📝 3.3 Documentation
- [ ] Update GlossaryModal with sell signals section
- [ ] Add "When to SELL" guidance
- [ ] Explain difference between model sell and rule-based exits

---

## Phase 4: Combined Exit Strategy

### 📝 4.1 Logic
- [ ] Priority: Model entry (BUY/SELL/HOLD)
- [ ] Layer: Rule-based exits for active positions
- [ ] Show both to users (model says X, rules suggest exit in Y days)

### 📝 4.2 API Response
- [ ] Add `entry_signal` (from model)
- [ ] Add `exit_guidance` (from rules)
- [ ] Add `sell_signal` (from model, Phase 2)
- [ ] Example:
  ```json
  {
    "symbol": "AAPL",
    "entry_signal": {"verdict": "BUY", "confidence": 0.75},
    "sell_signal": {"verdict": "HOLD", "confidence": 0.30},
    "exit_guidance": {
      "days_remaining": 3,
      "stop_loss_distance": 2.5,
      "risks": ["Signal decaying"]
    }
  }
  ```

### 📝 4.3 Frontend
- [ ] Show all three layers on detail page
- [ ] "Should I enter?" → Entry signal
- [ ] "When do I exit?" → Exit rules + sell signal

---

## Acceptance Criteria

### Exit Rules (Phase 1)
- [x] Service exists and has three exit triggers
- [ ] API endpoint returns exit status
- [ ] Frontend displays exit guidance with no errors
- [ ] Stop-loss correctly calculated
- [ ] Time-based correctly shows days remaining
- [ ] Signal decay triggers at 0.45 threshold

### Sell Classifier (Phase 2)
- [ ] Models trained and saved
- [ ] Training accuracy > 50% (random baseline)
- [ ] Sell signals on historical test set make sense
- [ ] Backend loads both models without errors
- [ ] API returns both buy_conf and sell_conf

### Combined (Phase 3-4)
- [ ] Dashboard shows BUY, MODERATE, SELL, WEAK_SELL, HOLD
- [ ] User can see why (model entry + exit rules)
- [ ] Sell signals and exit rules don't contradict
- [ ] Documentation explains all three layers
- [ ] Retail investor understands the guidance

---

## Files to Create/Modify

| File | Action | Status |
|------|--------|--------|
| `app/exit_rules.py` | Create | ✅ |
| `app/main.py` | Modify (add endpoint) | 🔄 |
| `app/routes.py` | Modify (add exit endpoint) | 🔄 |
| `app/schemas.py` | Modify (add ExitStatus schema) | 🔄 |
| `frontend/src/components/PositionExitGuidance.tsx` | Create | 🔄 |
| `frontend/src/components/SignalCard.tsx` | Modify (add sell signals) | 📝 |
| `src/04_label_construction.py` | Modify (add SELL label) | 📝 Phase 2 |
| `src/06_train_model.py` | Modify (train SELL model) | 📝 Phase 2 |
| `app/EXIT_RULES_INTEGRATION.py` | Create (guide) | ✅ |
| `docs/HONEST_SIGNAL_ARCHITECTURE.md` | Create (doc) | ✅ |
| `docs/EXIT_RULES_GUIDE.md` | Create (user guide) | 📝 |

---

## Testing Strategy

### Unit Tests
```python
# test_exit_rules.py
test_time_based_exit()       # Entry 10 days ago → should_exit=True
test_stop_loss_exit()        # Price down 5% → should_exit=True
test_signal_decay_exit()     # Confidence 0.40 → should_exit=True
test_no_exit_needed()        # Normal scenario → should_exit=False
```

### Integration Tests
```python
# test_api_exit_check.py
test_post_exit_check()       # API returns ExitStatus
test_exit_check_schema()     # Response matches schema
test_invalid_dates()         # Error handling
```

### E2E Tests
```python
# test_frontend_exit_display.tsx
test_renders_exit_guidance()       # Component displays
test_shows_days_remaining()        # 3/10 days shown
test_shows_return_percentage()     # -3.5% shown
test_highlights_risks()            # Red warning if risks
```

### Business Logic Tests
```python
# test_exit_rules_logic.py
test_stop_loss_at_5_pct()          # 5% exactly triggers
test_stop_loss_at_4_9_pct()        # 4.9% doesn't trigger
test_signal_threshold_exact()      # 0.45 exactly triggers
test_signal_threshold_above()      # 0.451 doesn't trigger
```

---

## Timeline Estimate

- **Phase 1 (Exit Rules Integration):** 2-3 hours
  - Backend: 30 min (endpoint + schema)
  - Frontend: 1 hour (component + styling)
  - Testing: 1 hour (unit + E2E)
  
- **Phase 2 (Sell Classifier):** 3-4 hours
  - Label prep: 30 min
  - Training: 2 hours (actual model training)
  - Integration: 1 hour
  
- **Phase 3 (Combined UI):** 2 hours
  - SignalCard updates: 1 hour
  - Documentation: 1 hour

**Total:** ~7-9 hours of work

---

## Success Metrics

✅ **Exit Rules Phase:**
- Positions show correct days remaining
- Stop-loss distance accurate to 0.1%
- No frontend errors or crashes
- Retail user can understand the guidance

✅ **Sell Classifier Phase:**
- Models train successfully
- Sell signals appear on dashboard
- Sell and buy signals rarely conflict
- Backtest shows improvement over single model

✅ **Combined Phase:**
- Users can see three layers (entry/exit/sell)
- 100% of positions show exit guidance
- Zero jargon in explanations
- Confidence that they can make informed decisions
