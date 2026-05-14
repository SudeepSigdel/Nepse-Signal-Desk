# NEPSE AI Signals — Frontend

React + TypeScript + Vite dashboard for viewing stock signals and technical analysis.

## Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend running at `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Create .env.local from .env.example
cp .env.example .env.local

# Start development server
npm run dev
```

The app will open at `http://localhost:3000` and auto-reload on changes.

## Build for Production

```bash
npm run build
npm run preview
```

Output is in the `dist/` directory, ready to serve from any static host.

## Project Structure

```
frontend/
├── public/               # Static assets
│   └── index.html
├── src/
│   ├── components/      # React components
│   │   ├── DashboardOverview.tsx   # Main dashboard view
│   │   └── StockChart.tsx          # Chart component (TODO)
│   ├── hooks/           # Custom React hooks
│   │   └── useStocks.ts            # API data fetching
│   ├── App.tsx          # Root component
│   ├── index.tsx        # Entry point
│   ├── config.ts        # Configuration
│   └── styles/          # Styles
├── vite.config.ts       # Vite configuration
├── tsconfig.json        # TypeScript config
└── package.json         # Dependencies
```

## Key Components

- **DashboardOverview**: Main dashboard showing top signals, search, and stats
- **StockChart**: (TODO) Interactive candlestick chart with indicators
- **useStocks**: Hook for fetching and caching stock data from API

## API Endpoints Used

- `GET /health` — Health check
- `GET /api/stocks` — List all stocks above threshold
- `GET /api/stocks/{symbol}` — Detailed OHLCV + indicators
- `GET /api/signal/{symbol}` — ML signal + explanation
- `GET /api/summary` — Top 10 signals

## Styling

Uses **Tailwind CSS** for styling. Configuration is in `package.json` and `src/index.css`.

To customize, edit `tailwind.config.js` or modify class names in components.

## Development Notes

- **Hot reload**: Vite automatically reloads on file changes
- **Type checking**: Run `npm run type-check` before committing
- **CORS**: Backend must allow `http://localhost:3000` in CORS origins
- **API errors**: Check browser console and backend logs for debugging

## TODO / Next Steps

- [ ] Build StockChart component with TradingView Lightweight Charts
- [ ] Add stock detail page (route: `/stocks/:symbol`)
- [ ] Add signal history table with filters
- [ ] Add user authentication (login/signup)
- [ ] Add watchlist management
- [ ] Add alert preferences UI
- [ ] Deploy to Vercel or Netlify
- [ ] Add error boundaries and fallback UI
- [ ] Add loading skeletons for better UX
- [ ] Add dark/light mode toggle

## Deployment

### Vercel

```bash
npm i -g vercel
vercel deploy
```

### Netlify

```bash
npm i -g netlify-cli
netlify deploy --prod --dir dist
```

### Self-hosted

```bash
npm run build
# Serve dist/ with nginx or any static host
```

Ensure backend CORS allows your frontend URL.

## Troubleshooting

**CORS error**: Backend CORS_ORIGINS must include your frontend URL
**API not responding**: Check backend is running (`python -m uvicorn app.main:app --reload`)
**Port 3000 in use**: Change in `vite.config.ts` or kill process
**Build errors**: Delete `node_modules` and `package-lock.json`, then reinstall

## License

MIT
