# Phase 3 Implementation: Frontend 5-Level Signals

**Status:** ✅ Completed  
**Date:** 2026-05-14  

---

## What Was Done

### ✅ 1. Updated SignalCard Component
**File:** `frontend/src/components/SignalCard.tsx`

**Changes:**
- Added support for `buy_confidence` and `sell_confidence` (optional)
- Added visual support for 5 verdict colors: green, amber, gray, yellow, red
- Displays appropriate confidence bar based on verdict type
- Shows both BUY and SELL confidence when available
- Updated action steps for all 5 levels
- Updated risk descriptions for all 5 levels

**Color Mapping:**
```
🟢 Green  = Strong BUY (buy_conf >= 0.65)
🟠 Amber  = Moderate BUY (buy_conf 0.55-0.65)
⚪ Gray   = HOLD (no clear signal)
🟡 Yellow = Weak SELL (sell_conf 0.55-0.65)
🔴 Red    = SELL (sell_conf >= 0.65)
```

---

## Remaining Phase 3 Tasks

### 2. **Update Dashboard Component** (Next)
**File:** `frontend/src/components/DashboardOverview.tsx`

**What to change:**
- Update type definitions to handle 5 verdict types instead of 3 tiers
- Change filter buttons from "High/Medium/Low" to "BUY/MODERATE/SELL/WEAK_SELL/HOLD"
- Update stock data fetching to handle `buy_confidence` and `sell_confidence`
- Update table display to show verdict types with colors
- Update sorting logic if needed

**Key points:**
- Currently filters by `tier` (High/Medium/Low)
- New system uses `verdict` (5 levels based on confidence scores)
- Need to compute verdict from API response in component
- Keep existing UI structure, just update the data display

**Estimated time:** 30-45 min

---

### 3. **Update GlossaryModal Component** (After Dashboard)
**File:** `frontend/src/components/GlossaryModal.tsx`

**What to add:**
- New tab or section explaining SELL signals
- Explain difference between BUY and SELL confidence
- Examples of each 5-level verdict
- When to be cautious vs confident
- Risk considerations

**Content to add:**
```
Tab: "5-Level Signals"
- What each level means
- Green: Safe to buy
- Amber: Wait for better entry
- Yellow: Some downside risk
- Red: High downside, avoid buying
- Gray: No clear direction, hold

Tab: "How It Works"
- Two models working together
- BUY model: will it go up?
- SELL model: will it go down?
- Why separate models?
```

**Estimated time:** 20-30 min

---

### 4. **Update Stock Detail Page** (After Glossary)
**File:** `frontend/src/components/StockDetailPage.tsx`

**What to change:**
- Display both buy and sell confidence prominently
- Call new API endpoint format (includes both confidences)
- Update SignalCard props to pass both confidences
- Update section headers to reflect 5-level system
- Ensure position exit guidance still displays

**Current structure:**
- Fetches `/api/signal/{symbol}`
- Passes to SignalCard component
- Shows position exit guidance below

**New structure:**
- Same fetch
- Now includes `sell_confidence`
- Pass both confidences to SignalCard
- Position exit unchanged (still from Phase 1)

**Estimated time:** 20-30 min

---

## Quick Implementation Guide

### Step 1: Update Dashboard
```tsx
// OLD
type TierFilter = 'High' | 'Medium' | 'Low'
interface Stock {
  tier: string
  confidence: number
}

// NEW
type VerdictFilter = 'all' | 'BUY' | 'MODERATE' | 'SELL' | 'WEAK_SELL' | 'HOLD'
interface Stock {
  verdict: string  // Computed from buy/sell confidence
  buy_confidence: number
  sell_confidence?: number
}

// Compute verdict from API response
function getVerdict(buyConf: number, sellConf?: number): string {
  if (buyConf >= 0.65) return 'BUY'
  if (buyConf >= 0.55) return 'MODERATE'
  if (sellConf && sellConf >= 0.65) return 'SELL'
  if (sellConf && sellConf >= 0.55) return 'WEAK_SELL'
  return 'HOLD'
}
```

### Step 2: Update Filter Buttons
```tsx
// OLD
{ label: 'High', value: 'High' }
{ label: 'Medium', value: 'Medium' }
{ label: 'Low / Neutral', value: 'Low' }

// NEW
{ label: '🟢 BUY', value: 'BUY' }
{ label: '🟠 MODERATE', value: 'MODERATE' }
{ label: '🟡 SELL', value: 'SELL' }
{ label: '🟡 WEAK SELL', value: 'WEAK_SELL' }
{ label: '⚪ HOLD', value: 'HOLD' }
```

### Step 3: Update Table
```tsx
// Update column showing verdict with color
<td className={`px-5 py-4 ${getVerdictColor(stock.verdict)}`}>
  {stock.verdict}
</td>

// Helper function
function getVerdictColor(verdict: string) {
  switch(verdict) {
    case 'BUY': return 'text-green-400'
    case 'MODERATE': return 'text-amber-400'
    case 'SELL': return 'text-red-400'
    case 'WEAK_SELL': return 'text-yellow-400'
    case 'HOLD': return 'text-gray-400'
  }
}
```

---

## API Response Format to Expect

After Phase 2 training, API returns:

```json
{
  "symbol": "ABC",
  "buy_confidence": 0.72,
  "sell_confidence": 0.28,
  "verdict": "Strong buy signal",
  "verdict_color": "green",
  "description": "...",
  "thresholds": {
    "buy_high": 0.65,
    "buy_medium": 0.55,
    "buy_low": 0.45
  }
}
```

---

## Testing Checklist (After Each Change)

- [ ] No TypeScript errors: `npm run type-check`
- [ ] Component renders: Check browser
- [ ] All 5 verdict levels display: Test with different stocks
- [ ] Colors correct: Visual inspection
- [ ] Filters work: Click each filter button
- [ ] Responsive on mobile: Test with device emulator
- [ ] No console warnings: Check DevTools

---

## Estimated Total Time for Remaining Tasks

| Task | Time |
|------|------|
| Update Dashboard | 45 min |
| Update Glossary | 30 min |
| Update Stock Detail | 30 min |
| Testing (all components) | 30 min |
| **Total** | **~2.5 hours** |

---

## Success Criteria

✅ Dashboard displays 5 verdict types  
✅ All filter buttons work  
✅ Stock detail shows both confidences  
✅ Glossary explains new signals  
✅ All 5 colors display correctly  
✅ No TypeScript errors  
✅ Responsive design maintained  
✅ Position exit still works  

---

## Files Modified Today

- ✅ `frontend/src/components/SignalCard.tsx` — Updated for 5-level signals

## Files to Modify Next

- `frontend/src/components/DashboardOverview.tsx` — Update filters/display
- `frontend/src/components/GlossaryModal.tsx` — Add SELL explanation
- `frontend/src/components/StockDetailPage.tsx` — Display both confidences

---

## Notes

1. **Backward Compatibility:** If SELL model not trained, `sell_confidence` will be `null` in API response. SignalCard already handles this gracefully.

2. **Data Type:** Current Dashboard expects `tier` field. With new API, need to compute `verdict` from confidences.

3. **Sorting:** May want to sort by `buy_confidence` instead of alphabetically by verdict.

4. **Colors:** Use TailwindCSS classes consistently:
   - Green: `text-green-400`, `bg-green-500/10`
   - Amber: `text-amber-400`, `bg-amber-500/10`
   - Yellow: `text-yellow-400`, `bg-yellow-500/10`
   - Red: `text-red-400`, `bg-red-500/10`
   - Gray: `text-gray-400`, `bg-gray-500/10`

---

## Next: Ready to Update Dashboard?

Start with `frontend/src/components/DashboardOverview.tsx`

Key changes:
1. Update type definitions
2. Add verdict computation function
3. Update filter buttons
4. Update table display
5. Test in browser

Estimated: 45 minutes

Ready to proceed?
