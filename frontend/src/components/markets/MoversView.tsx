import { Link } from 'react-router-dom'
import { useStocksContext } from '../../context/StocksContext'
import { formatPercent, formatPrice } from '../../lib/format'
import type { Stock } from '../../types'

interface MoversSection {
  key: string
  title: string
  caption: string
  items: Stock[]
  metric: (stock: Stock) => { text: string; className?: string }
}

function MoversColumn({ section }: { section: MoversSection }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="border-b border-zinc-100 px-3 py-2 dark:border-zinc-800">
        <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">{section.title}</p>
        <p className="text-[11px] text-zinc-400 dark:text-zinc-500">{section.caption}</p>
      </div>
      {section.items.length === 0 ? (
        <p className="px-3 py-4 text-xs text-zinc-400 dark:text-zinc-500">No data available.</p>
      ) : (
        <ul>
          {section.items.map((stock) => {
            const metric = section.metric(stock)
            return (
              <li key={stock.symbol} className="border-b border-zinc-50 last:border-0 dark:border-zinc-800/60">
                <Link
                  to={`/stocks/${stock.symbol}`}
                  className="flex items-center justify-between gap-2 px-3 py-2 text-xs hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
                >
                  <span className="flex items-baseline gap-2">
                    <span className="font-medium text-zinc-800 dark:text-zinc-200">{stock.symbol}</span>
                    <span className="tabular-nums text-zinc-400 dark:text-zinc-500">{formatPrice(stock.close)}</span>
                  </span>
                  <span className={`tabular-nums font-medium ${metric.className ?? 'text-zinc-500 dark:text-zinc-400'}`}>
                    {metric.text}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function formatTurnover(value: number | null): string {
  if (value === null) return '—'
  if (value >= 1e7) return `Rs ${(value / 1e7).toFixed(2)}cr`
  if (value >= 1e5) return `Rs ${(value / 1e5).toFixed(2)}lk`
  return `Rs ${Math.round(value).toLocaleString('en-IN')}`
}

export function MoversView() {
  const { stocks, loading } = useStocksContext()

  const withChange = stocks.filter((s) => s.change_pct !== null)
  const gainers = [...withChange].sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0)).slice(0, 10)
  const losers = [...withChange].sort((a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0)).slice(0, 10)

  const withTurnover = stocks.filter((s) => s.turnover !== null)
  const highTurnover = [...withTurnover].sort((a, b) => (b.turnover ?? 0) - (a.turnover ?? 0)).slice(0, 10)

  const withVolumeRatio = stocks.filter((s) => s.volume_ratio !== null)
  const mostActive = [...withVolumeRatio].sort((a, b) => (b.volume_ratio ?? 0) - (a.volume_ratio ?? 0)).slice(0, 10)

  const sections: MoversSection[] = [
    {
      key: 'gainers',
      title: 'Top gainers',
      caption: "Today's % change",
      items: gainers,
      metric: (s) => ({
        text: formatPercent(s.change_pct, { signed: true }),
        className: 'text-emerald-600 dark:text-emerald-400',
      }),
    },
    {
      key: 'losers',
      title: 'Top losers',
      caption: "Today's % change",
      items: losers,
      metric: (s) => ({
        text: formatPercent(s.change_pct, { signed: true }),
        className: 'text-rose-600 dark:text-rose-400',
      }),
    },
    {
      key: 'turnover',
      title: 'Highest turnover',
      caption: 'Value traded today',
      items: highTurnover,
      metric: (s) => ({ text: formatTurnover(s.turnover) }),
    },
    {
      key: 'active',
      title: 'Most active',
      caption: 'Volume vs. own average',
      items: mostActive,
      metric: (s) => ({
        text: s.volume_ratio !== null ? `${s.volume_ratio.toFixed(1)}×` : '—',
        className: 'text-blue-600 dark:text-blue-400',
      }),
    },
  ]

  if (loading && stocks.length === 0) {
    return <p className="text-sm text-zinc-400 dark:text-zinc-500">Loading market data…</p>
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {sections.map((section) => (
        <MoversColumn key={section.key} section={section} />
      ))}
    </div>
  )
}
