import { ChevronDown, ChevronUp, Inbox } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatDateShort, formatPrice } from '../../lib/format'
import { rsiZone, VOLUME_STATE_LABEL, volumeState } from '../../lib/verdict'
import type { Stock } from '../../types'
import { ConfidenceMeter } from '../ui/ConfidenceMeter'
import { EmptyState } from '../ui/EmptyState'
import { ErrorState } from '../ui/ErrorState'
import { SignalBadge } from '../ui/SignalBadge'
import { TableRowSkeleton } from '../ui/Skeleton'
import { Tooltip } from '../ui/Tooltip'
import { trendFromDelta, TrendIndicator } from '../ui/TrendIndicator'
import { WatchlistStarButton } from '../ui/WatchlistStarButton'

type SortKey = 'confidence' | 'close' | 'sell_confidence' | 'rsi'

function SortableHeader({
  label,
  sortKey,
  active,
  direction,
  onSort,
  tooltip,
}: {
  label: string
  sortKey: SortKey
  active: boolean
  direction: 'asc' | 'desc'
  onSort: (key: SortKey) => void
  tooltip?: string
}) {
  return (
    <th className="px-3 py-2 text-right font-medium">
      <button
        onClick={() => onSort(sortKey)}
        className="inline-flex items-center gap-1 whitespace-nowrap text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200"
      >
        {label}
        {tooltip && <Tooltip label={tooltip} />}
        {active && (direction === 'desc' ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />)}
      </button>
    </th>
  )
}

export function StockTable({
  stocks,
  baseline,
  loading,
  error,
  onRetry,
}: {
  stocks: Stock[]
  baseline: Record<string, number>
  loading: boolean
  error: string | null
  onRetry: () => void
}) {
  const [sortKey, setSortKey] = useState<SortKey>('confidence')
  const [direction, setDirection] = useState<'asc' | 'desc'>('desc')

  const sorted = useMemo(() => {
    const withValue = stocks.map((s) => {
      const value =
        sortKey === 'confidence'
          ? s.confidence
          : sortKey === 'close'
            ? (s.close ?? -Infinity)
            : sortKey === 'sell_confidence'
              ? (s.sell_confidence ?? -Infinity)
              : (s.rsi ?? -Infinity)
      return { stock: s, value }
    })
    withValue.sort((a, b) => (direction === 'desc' ? b.value - a.value : a.value - b.value))
    return withValue.map((x) => x.stock)
  }, [stocks, sortKey, direction])

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setDirection((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setDirection('desc')
    }
  }

  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />
  }

  if (!loading && stocks.length === 0) {
    return (
      <EmptyState
        icon={Inbox}
        title="No stocks match this filter"
        description="Try a different filter, or check back after the next data refresh."
      />
    )
  }

  return (
    <div className="thin-scrollbar overflow-x-auto rounded-md border border-zinc-200 dark:border-zinc-800">
      <table className="w-full min-w-[880px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
            <th className="px-3 py-2 text-left font-medium">Symbol</th>
            <th className="px-3 py-2 text-left font-medium">Sector</th>
            <SortableHeader label="Close" sortKey="close" active={sortKey === 'close'} direction={direction} onSort={handleSort} />
            <th className="px-3 py-2 text-left font-medium">
              <span className="inline-flex items-center gap-1">
                Buy confidence
                <Tooltip label="Model-estimated probability the stock rises more than 1% over the next 10 trading days." />
              </span>
            </th>
            <th className="px-3 py-2 text-left font-medium">
              <span className="inline-flex items-center gap-1">
                Sell confidence
                <Tooltip label="Model-estimated probability the stock falls more than 1% over the next 10 trading days." />
              </span>
            </th>
            <th className="px-3 py-2 text-left font-medium">Verdict</th>
            <th className="px-3 py-2 text-left font-medium">Trend</th>
            <SortableHeader
              label="RSI"
              sortKey="rsi"
              active={sortKey === 'rsi'}
              direction={direction}
              onSort={handleSort}
              tooltip="Relative Strength Index. Below 30 is oversold, above 70 is overbought."
            />
            <th className="px-3 py-2 text-left font-medium">Volume</th>
            <th className="px-3 py-2 text-left font-medium">As of</th>
            <th className="px-3 py-2 text-center font-medium">
              <span className="sr-only">Watchlist</span>
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
          {loading &&
            stocks.length === 0 &&
            Array.from({ length: 10 }).map((_, i) => <TableRowSkeleton key={i} columns={11} />)}

          {sorted.map((stock) => {
            const delta = baseline[stock.symbol] !== undefined ? stock.confidence - baseline[stock.symbol] : null
            const zone = rsiZone(stock.rsi)
            const vState = volumeState(stock.volume_ratio)

            return (
              <tr key={stock.symbol} className="group hover:bg-zinc-50 dark:hover:bg-zinc-900/60">
                <td className="px-3 py-2">
                  <Link to={`/stocks/${stock.symbol}`} className="font-medium text-zinc-900 hover:underline dark:text-zinc-100">
                    {stock.symbol}
                  </Link>
                </td>
                <td className="px-3 py-2 text-xs text-zinc-500 dark:text-zinc-400">{stock.sector ?? '—'}</td>
                <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatPrice(stock.close)}
                </td>
                <td className="px-3 py-2">
                  <ConfidenceMeter value={stock.buy_confidence ?? stock.confidence} tone="buy" className="w-28" />
                </td>
                <td className="px-3 py-2">
                  {stock.sell_confidence === null ? (
                    <span className="text-xs text-zinc-400 dark:text-zinc-600">—</span>
                  ) : (
                    <ConfidenceMeter value={stock.sell_confidence} tone="sell" className="w-28" />
                  )}
                </td>
                <td className="px-3 py-2">
                  <SignalBadge verdict={stock.verdict} />
                </td>
                <td className="px-3 py-2">
                  <TrendIndicator direction={trendFromDelta(delta)} />
                </td>
                <td className="px-3 py-2 tabular-nums text-zinc-700 dark:text-zinc-300">
                  {stock.rsi === null ? '—' : stock.rsi.toFixed(1)}
                  {zone !== 'neutral' && (
                    <span
                      className={`ml-1 text-[11px] ${zone === 'oversold' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}
                    >
                      {zone === 'oversold' ? 'oversold' : 'overbought'}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-xs text-zinc-500 dark:text-zinc-400">{VOLUME_STATE_LABEL[vState]}</td>
                <td className="px-3 py-2 text-xs text-zinc-500 dark:text-zinc-400">{formatDateShort(stock.date)}</td>
                <td className="px-3 py-2 text-center">
                  <WatchlistStarButton symbol={stock.symbol} size="sm" />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="border-t border-zinc-100 px-3 py-1.5 text-xs text-zinc-400 dark:border-zinc-800 dark:text-zinc-500">
        {sorted.length} stock{sorted.length === 1 ? '' : 's'}
      </div>
    </div>
  )
}
