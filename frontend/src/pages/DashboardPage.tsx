import { useMemo, useState } from 'react'
import { ActionBoard } from '../components/dashboard/ActionBoard'
import { MarketPulseStrip } from '../components/dashboard/MarketPulseStrip'
import { StockTable } from '../components/dashboard/StockTable'
import { useStocksContext } from '../context/StocksContext'
import { useConfidenceBaseline } from '../hooks/useConfidenceBaseline'
import { useWatchlist } from '../hooks/useWatchlist'
import { FilterBar, type FilterValue } from '../components/ui/FilterBar'
import { verdictGroup } from '../lib/verdict'

export function DashboardPage() {
  const { stocks, loading, error, refresh } = useStocksContext()
  const { symbols: watchlist } = useWatchlist()
  const baseline = useConfidenceBaseline(stocks)
  const [filter, setFilter] = useState<FilterValue>('all')

  const counts = useMemo(() => {
    const c: Partial<Record<FilterValue, number>> = { all: stocks.length }
    for (const s of stocks) {
      const g = verdictGroup(s.verdict)
      c[g] = (c[g] ?? 0) + 1
    }
    c.watchlist = stocks.filter((s) => watchlist.includes(s.symbol)).length
    return c
  }, [stocks, watchlist])

  const filtered = useMemo(() => {
    if (filter === 'all') return stocks
    if (filter === 'watchlist') return stocks.filter((s) => watchlist.includes(s.symbol))
    return stocks.filter((s) => verdictGroup(s.verdict) === filter)
  }, [stocks, filter, watchlist])

  return (
    <div className="mx-auto max-w-[1400px] space-y-5 p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Market dashboard</h1>
        <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
          What to pay attention to in the NEPSE market today.
        </p>
      </div>

      <MarketPulseStrip stocks={stocks} loading={loading && stocks.length === 0} />

      <ActionBoard stocks={stocks} />

      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">All stocks</h2>
          <FilterBar value={filter} onChange={setFilter} counts={counts} />
        </div>
        <StockTable stocks={filtered} baseline={baseline} loading={loading} error={error} onRetry={refresh} />
      </div>
    </div>
  )
}
