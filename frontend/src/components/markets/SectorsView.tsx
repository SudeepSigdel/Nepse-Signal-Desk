import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useStocksContext } from '../../context/StocksContext'
import { formatConfidence, formatPrice } from '../../lib/format'
import { verdictGroup } from '../../lib/verdict'
import { SignalBadge } from '../ui/SignalBadge'

interface SectorAggregate {
  sector: string
  count: number
  avgConfidence: number
  buy: number
  watch: number
  sellRisk: number
}

export function SectorsView() {
  const { stocks, loading } = useStocksContext()
  const [selected, setSelected] = useState<string | null>(null)

  const sectors = useMemo<SectorAggregate[]>(() => {
    const groups = new Map<string, typeof stocks>()
    for (const s of stocks) {
      const key = s.sector ?? 'Unclassified'
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push(s)
    }

    return Array.from(groups.entries())
      .map(([sector, items]) => ({
        sector,
        count: items.length,
        avgConfidence: items.reduce((sum, s) => sum + s.confidence, 0) / items.length,
        buy: items.filter((s) => verdictGroup(s.verdict) === 'buy').length,
        watch: items.filter((s) => verdictGroup(s.verdict) === 'watch').length,
        sellRisk: items.filter((s) => verdictGroup(s.verdict) === 'sell_risk').length,
      }))
      .sort((a, b) => b.avgConfidence - a.avgConfidence)
  }, [stocks])

  const selectedStocks = useMemo(() => {
    if (!selected) return []
    return stocks.filter((s) => (s.sector ?? 'Unclassified') === selected).sort((a, b) => b.confidence - a.confidence)
  }, [stocks, selected])

  if (loading && stocks.length === 0) {
    return <p className="text-sm text-zinc-400 dark:text-zinc-500">Loading sector data…</p>
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
              <th className="px-3 py-2 text-left font-medium">Sector</th>
              <th className="px-3 py-2 text-right font-medium">Stocks</th>
              <th className="px-3 py-2 text-right font-medium">Avg. confidence</th>
              <th className="px-3 py-2 text-right font-medium">Buy / Watch / Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
            {sectors.map((row) => (
              <tr
                key={row.sector}
                onClick={() => setSelected(row.sector === selected ? null : row.sector)}
                className={`cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900/60 ${
                  selected === row.sector ? 'bg-zinc-50 dark:bg-zinc-900/60' : ''
                }`}
              >
                <td className="px-3 py-2 font-medium text-zinc-900 dark:text-zinc-100">{row.sector}</td>
                <td className="px-3 py-2 text-right tabular-nums text-zinc-600 dark:text-zinc-400">{row.count}</td>
                <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">
                  {formatConfidence(row.avgConfidence)}
                </td>
                <td className="px-3 py-2 text-right text-xs tabular-nums">
                  <span className="text-emerald-600 dark:text-emerald-400">{row.buy}</span>
                  {' / '}
                  <span className="text-amber-600 dark:text-amber-400">{row.watch}</span>
                  {' / '}
                  <span className="text-rose-600 dark:text-rose-400">{row.sellRisk}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
        <div className="border-b border-zinc-100 px-3 py-2 dark:border-zinc-800">
          <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
            {selected ?? 'Select a sector'}
          </p>
          <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
            {selected ? `${selectedStocks.length} stocks, ranked by buy confidence` : 'Click a row to see its stocks'}
          </p>
        </div>
        {selected && (
          <ul>
            {selectedStocks.map((stock) => (
              <li key={stock.symbol} className="border-b border-zinc-50 last:border-0 dark:border-zinc-800/60">
                <Link
                  to={`/stocks/${stock.symbol}`}
                  className="flex items-center justify-between gap-2 px-3 py-2 text-xs hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
                >
                  <span className="flex items-baseline gap-2">
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{stock.symbol}</span>
                    <span className="tabular-nums text-zinc-400 dark:text-zinc-500">{formatPrice(stock.close)}</span>
                  </span>
                  <SignalBadge verdict={stock.verdict} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
