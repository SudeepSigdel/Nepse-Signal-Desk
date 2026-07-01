import { Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ConfidenceMeter } from '../components/ui/ConfidenceMeter'
import { EmptyState } from '../components/ui/EmptyState'
import { SignalBadge } from '../components/ui/SignalBadge'
import { trendFromDelta, TrendIndicator } from '../components/ui/TrendIndicator'
import { useStocksContext } from '../context/StocksContext'
import { useConfidenceBaseline } from '../hooks/useConfidenceBaseline'
import { useWatchlist } from '../hooks/useWatchlist'
import { formatPrice } from '../lib/format'
import { verdictGroup } from '../lib/verdict'

export function WatchlistPage() {
  const { stocks, loading } = useStocksContext()
  const { symbols, remove } = useWatchlist()
  const baseline = useConfidenceBaseline(stocks)

  const watchedStocks = symbols
    .map((sym) => stocks.find((s) => s.symbol === sym))
    .filter((s): s is NonNullable<typeof s> => Boolean(s))

  const unresolvedSymbols = symbols.filter((sym) => !stocks.some((s) => s.symbol === sym))

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Watchlist</h1>
        <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
          Symbols you're personally tracking, with today's verdict and confidence movement.
        </p>
      </div>

      {symbols.length === 0 ? (
        <EmptyState
          icon={Star}
          title="Your watchlist is empty"
          description="Star a stock from the dashboard or a research page to track it here."
        />
      ) : loading && watchedStocks.length === 0 ? (
        <p className="text-sm text-zinc-400 dark:text-zinc-500">Loading watchlist…</p>
      ) : (
        <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
                <th className="px-3 py-2 text-left font-medium">Symbol</th>
                <th className="px-3 py-2 text-right font-medium">Close</th>
                <th className="px-3 py-2 text-left font-medium">Buy confidence</th>
                <th className="px-3 py-2 text-left font-medium">Verdict</th>
                <th className="px-3 py-2 text-left font-medium">Change today</th>
                <th className="px-3 py-2 text-left font-medium">Alert</th>
                <th className="px-3 py-2 text-right font-medium">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
              {watchedStocks.map((stock) => {
                const delta = baseline[stock.symbol] !== undefined ? stock.confidence - baseline[stock.symbol] : null
                const isRisk = verdictGroup(stock.verdict) === 'sell_risk'
                const isWeakening = delta !== null && delta < -0.02
                return (
                  <tr key={stock.symbol} className="hover:bg-zinc-50 dark:hover:bg-zinc-900/60">
                    <td className="px-3 py-2">
                      <Link to={`/stocks/${stock.symbol}`} className="font-medium text-zinc-900 hover:underline dark:text-zinc-100">
                        {stock.symbol}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                      {formatPrice(stock.close)}
                    </td>
                    <td className="px-3 py-2">
                      <ConfidenceMeter value={stock.buy_confidence ?? stock.confidence} tone="buy" className="w-28" />
                    </td>
                    <td className="px-3 py-2">
                      <SignalBadge verdict={stock.verdict} />
                    </td>
                    <td className="px-3 py-2">
                      <TrendIndicator direction={trendFromDelta(delta)} />
                    </td>
                    <td className="px-3 py-2 text-xs">
                      {isRisk ? (
                        <span className="text-rose-600 dark:text-rose-400">Downside risk elevated</span>
                      ) : isWeakening ? (
                        <span className="text-amber-600 dark:text-amber-400">Confidence weakening</span>
                      ) : (
                        <span className="text-zinc-300 dark:text-zinc-600">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        onClick={() => remove(stock.symbol)}
                        className="text-xs font-medium text-zinc-400 hover:text-rose-600 dark:text-zinc-500 dark:hover:text-rose-400"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                )
              })}

              {unresolvedSymbols.map((sym) => (
                <tr key={sym}>
                  <td className="px-3 py-2 font-medium text-zinc-400 dark:text-zinc-600">{sym}</td>
                  <td colSpan={5} className="px-3 py-2 text-xs text-zinc-400 dark:text-zinc-600">
                    Not in the current model-ready universe (illiquid or missing data).
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => remove(sym)}
                      className="text-xs font-medium text-zinc-400 hover:text-rose-600 dark:text-zinc-500 dark:hover:text-rose-400"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
