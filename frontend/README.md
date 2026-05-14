# Frontend — NEPSE Signal Desk

React + TypeScript + Vite dashboard for NEPSE stock signals.

## Quick Start

```bash
npm install
cp .env.example .env.local   # set VITE_API_BASE_URL=http://localhost:8000
npm run dev                   # → http://localhost:5173
npm run build                 # production build → dist/
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

## Structure

```
src/
├── App.tsx                          # Router: / and /stocks/:symbol
├── config.ts                        # API_BASE_URL, APP_TITLE, REFRESH_INTERVAL_MS
├── hooks/useStocks.ts               # useStocks, useStockDetail, useSignal
└── components/
    ├── DashboardOverview.tsx        # Signal table, filters, KPI summary
    ├── StockDetailPage.tsx          # Charts, signal card, position tracker
    ├── StockChart.tsx               # Candlestick + RSI + MACD + Volume
    ├── SignalCard.tsx               # Confidence bars, verdict, action steps
    ├── PositionExitGuidance.tsx     # Days held, return %, stop-loss distance
    ├── RiskPanel.tsx                # Accuracy disclosure, portfolio tips
    └── GlossaryModal.tsx            # Learning center (RSI, MACD, signals)
```

## Key Details

**Verdict logic** (`DashboardOverview.tsx`):
```ts
buy_conf >= 0.65             → BUY
buy_conf >= 0.55             → MODERATE
sell_conf >= 0.65            → SELL
sell_conf >= 0.55            → WEAK_SELL
else                         → HOLD
```

**Caching** (`useStocks.ts`): All three hooks cache responses for 5 minutes at module level.

**Position exit check**: `StockDetailPage` calls `POST /api/positions/exit-check` whenever entry date or entry price changes. The `ExitStatus` type is exported from `PositionExitGuidance.tsx` and imported by `StockDetailPage`.

## Troubleshooting

| Problem | Fix |
|---|---|
| CORS error | Add `http://localhost:5173` to backend `CORS_ORIGINS` |
| API not found | Check `VITE_API_BASE_URL` in `.env.local` |
| Type errors | Run `npm run type-check` |
| Build fails | Delete `node_modules/` and reinstall |
