# Frontend — NEPSE Signal Desk

React + TypeScript + Vite dashboard for NEPSE stock signals, accounts, and portfolio tracking.

## Quick Start

```bash
npm install
npm run dev                   # → http://localhost:3000
npm run build                 # production build → dist/
npm run type-check            # tsc --noEmit
```

Local dev talks to the backend at `http://localhost:8000` by default (see `src/config.ts`). Override with `VITE_API_BASE_URL` in a `.env.local`. Production builds read `.env.production` (`VITE_API_BASE_URL`, no secrets, committed).

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API URL |

## Structure

```
src/
├── App.tsx                    # Routes (lazy-loaded pages) + AuthProvider/UserDataProvider/StocksProvider nesting
├── config.ts                  # API_BASE_URL, APP_TITLE, REFRESH_INTERVAL_MS
├── types.ts                   # Shared types mirroring app/schemas.py response shapes
├── pages/                     # DashboardPage, MarketsPage, WatchlistPage, PortfolioPage,
│                               # TrustPage, StockResearchPage, Login/Signup/AuthCallbackPage
├── components/
│   ├── dashboard/              # StockTable, ActionBoard
│   ├── stock/                  # StockHeader, StockChart (lightweight-charts candlesticks),
│   │                            # SignalSummaryPanel, SignalHistoryPanel, PositionHelper, ModelContextPanel
│   ├── markets/                 # MoversView, SectorsView
│   ├── layout/                  # AppShell, TopBar, Sidebar, BottomNav, navItems
│   ├── auth/                    # ProtectedRoute
│   └── ui/                      # SignalBadge, ConfidenceMeter, Tooltip, WatchlistStarButton, …
├── context/
│   ├── AuthContext.tsx          # JWT session state, login/signup/logout
│   ├── UserDataContext.tsx      # Shared watchlist/holdings (backend-persisted), one fetch for the whole app
│   └── StocksContext.tsx        # Shared /api/stocks feed + selected model family
├── hooks/                       # useStocks, useSignal, useStockDetail, useModelPerformance,
│                                 # useWatchlist/usePositions (thin wrappers over UserDataContext), …
└── lib/                         # api.ts (axios + auth interceptor), chartTheme.ts, chartRegistry.ts, format.ts, verdict.ts
```

## Key Details

**Verdict logic** (`lib/verdict.ts` on the frontend, mirrors `app/services/signal_service.py`):
```ts
buy_conf >= 0.65             → BUY
buy_conf >= 0.55             → MODERATE
sell_conf >= 0.65            → SELL
sell_conf >= 0.55            → WEAK_SELL
else                         → HOLD
```

**Accounts**: `AuthContext` holds the JWT (in `localStorage`, attached to every request via an axios interceptor in `lib/api.ts`). `/watchlist` and `/portfolio` are wrapped in `ProtectedRoute` and redirect to `/login` if unauthenticated; the dashboard's star button does the same. On first login, any watchlist/holdings data that existed in `localStorage` from before accounts existed is imported into the account once, then cleared (`UserDataContext`).

**Charts**: the stock detail page uses TradingView's `lightweight-charts` for a real multi-pane candlestick chart (price+SMA+Bollinger, volume, RSI, MACD, one shared crosshair/time-scale). The Trust page and signal-history sparkline use Chart.js instead (ordinary bar/line charts) — both need `lib/chartRegistry.ts`/`lightweight-charts` imported before rendering; see comments in `StockChart.tsx` if adding a new chart.

**Code splitting**: every page except the dashboard is `React.lazy()`-loaded in `App.tsx` so the initial bundle doesn't pull in every page's dependencies (especially the two chart libraries).

**Position exit check**: `PositionHelper` (stock detail page) and `PortfolioPage` call `POST /api/positions/exit-check` to get live exit guidance for a tracked position.

**Model context**: BUY/SELL signals can be viewed as XGBoost, Random Forest, or a blend. The separate relative-strength score is XGBoost-only and compares a stock with the NEPSE universe; it is not an absolute profit signal. XGBoost plus relative strength refresh daily, while Random Forest refreshes weekly.

**Sentiment**: when news coverage exists, BUY/SELL models include a market-wide FinBERT sentiment feature. It is not symbol-specific news analysis; the UI wording in `TrustPage` and `ModelContextPanel` must preserve that distinction.

## Troubleshooting

| Problem | Fix |
|---|---|
| CORS error | Add `http://localhost:3000` to backend `CORS_ORIGINS` |
| API not found | Check `VITE_API_BASE_URL` (`.env.local` for dev, `.env.production` for prod builds) |
| Type errors | Run `npm run type-check` |
| Build fails | Delete `node_modules/` and reinstall |
| Watchlist/portfolio 401s | Backend needs `DATABASE_URL` set and `alembic upgrade head` applied — see root README |
