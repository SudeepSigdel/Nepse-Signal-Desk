import { formatPrice } from '../../lib/format'
import { SignalBadge } from '../ui/SignalBadge'
import { type TrendDirection, TrendIndicator } from '../ui/TrendIndicator'
import { WatchlistStarButton } from '../ui/WatchlistStarButton'

export function StockHeader({
  symbol,
  close,
  verdict,
  trend,
  sector,
}: {
  symbol: string
  close: number | null
  verdict: string | null
  trend: TrendDirection
  sector?: string | null
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 pb-4 dark:border-zinc-800">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{symbol}</h1>
        {sector && (
          <span className="inline-flex items-center whitespace-nowrap rounded border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 text-xs font-medium text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
            {sector}
          </span>
        )}
        <WatchlistStarButton symbol={symbol} />
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{formatPrice(close)}</span>
        <SignalBadge verdict={verdict} />
        <TrendIndicator direction={trend} />
      </div>
    </div>
  )
}
