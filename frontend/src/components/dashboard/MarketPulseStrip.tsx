import { useMemo } from 'react'
import { formatConfidence } from '../../lib/format'
import { verdictGroup } from '../../lib/verdict'
import type { Stock } from '../../types'

function Tile({ label, value, tone }: { label: string; value: string; tone?: 'buy' | 'watch' | 'sell' | 'neutral' }) {
  const toneClass =
    tone === 'buy'
      ? 'text-emerald-700 dark:text-emerald-400'
      : tone === 'watch'
        ? 'text-amber-700 dark:text-amber-400'
        : tone === 'sell'
          ? 'text-rose-700 dark:text-rose-400'
          : 'text-zinc-900 dark:text-zinc-100'

  return (
    <div className="flex-1 border-zinc-200 px-4 py-3 dark:border-zinc-800 sm:border-l sm:first:border-l-0">
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className={`mt-1 text-2xl font-semibold tabular-nums ${toneClass}`}>{value}</p>
    </div>
  )
}

export function MarketPulseStrip({ stocks, loading }: { stocks: Stock[]; loading: boolean }) {
  const stats = useMemo(() => {
    if (stocks.length === 0) return null
    const strongBuy = stocks.filter((s) => s.verdict === 'BUY').length
    const watch = stocks.filter((s) => verdictGroup(s.verdict) === 'watch').length
    const sellRisk = stocks.filter((s) => verdictGroup(s.verdict) === 'sell_risk').length
    const avgConfidence = stocks.reduce((sum, s) => sum + s.confidence, 0) / stocks.length
    return { scanned: stocks.length, strongBuy, watch, sellRisk, avgConfidence }
  }, [stocks])

  return (
    <div className="grid grid-cols-2 rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900 sm:flex">
      <Tile label="Stocks scanned" value={loading || !stats ? '—' : String(stats.scanned)} />
      <Tile label="Strong buy" value={loading || !stats ? '—' : String(stats.strongBuy)} tone="buy" />
      <Tile label="Watch" value={loading || !stats ? '—' : String(stats.watch)} tone="watch" />
      <Tile label="Sell risk" value={loading || !stats ? '—' : String(stats.sellRisk)} tone="sell" />
      <Tile label="Avg. confidence" value={loading || !stats ? '—' : formatConfidence(stats.avgConfidence)} />
    </div>
  )
}
