import { Link } from 'react-router-dom'
import { useConfidenceBaseline } from '../../hooks/useConfidenceBaseline'
import { useWatchlist } from '../../hooks/useWatchlist'
import { formatConfidence } from '../../lib/format'
import { verdictGroup } from '../../lib/verdict'
import type { Stock } from '../../types'

interface Section {
  key: string
  title: string
  caption: string
  items: Stock[]
  emptyText: string
  metric: (stock: Stock) => { text: string; className?: string }
}

function ActionBoardColumn({ section }: { section: Section }) {
  return (
    <div className="flex min-w-0 flex-col rounded-md border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      <div className="border-b border-zinc-100 px-3 py-2 dark:border-zinc-800">
        <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">{section.title}</p>
        <p className="text-[11px] text-zinc-400 dark:text-zinc-500">{section.caption}</p>
      </div>
      {section.items.length === 0 ? (
        <p className="px-3 py-4 text-xs text-zinc-400 dark:text-zinc-500">{section.emptyText}</p>
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
                  <span className="font-medium text-zinc-800 dark:text-zinc-200">{stock.symbol}</span>
                  <span className={`tabular-nums ${metric.className ?? 'text-zinc-500 dark:text-zinc-400'}`}>
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

export function ActionBoard({ stocks }: { stocks: Stock[] }) {
  const baseline = useConfidenceBaseline(stocks)
  const { symbols: watchlist } = useWatchlist()

  const strongest = [...stocks]
    .filter((s) => verdictGroup(s.verdict) === 'buy')
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 5)

  const withDelta = stocks
    .filter((s) => baseline[s.symbol] !== undefined)
    .map((s) => ({ stock: s, delta: s.confidence - baseline[s.symbol] }))

  const improved = withDelta
    .filter((x) => x.delta > 0.02)
    .sort((a, b) => b.delta - a.delta)
    .slice(0, 5)

  const weakened = withDelta
    .filter((x) => x.delta < -0.02)
    .sort((a, b) => a.delta - b.delta)
    .slice(0, 5)

  const sellRisk = [...stocks]
    .filter((s) => verdictGroup(s.verdict) === 'sell_risk')
    .sort((a, b) => (b.sell_confidence ?? 0) - (a.sell_confidence ?? 0))
    .slice(0, 5)

  const watchlistAlerts = stocks.filter((s) => {
    if (!watchlist.includes(s.symbol)) return false
    const delta = baseline[s.symbol] !== undefined ? s.confidence - baseline[s.symbol] : 0
    return verdictGroup(s.verdict) === 'sell_risk' || delta < -0.02
  })

  const sections: Section[] = [
    {
      key: 'strongest',
      title: 'Strongest opportunities',
      caption: 'Highest buy confidence',
      items: strongest,
      emptyText: 'No high-confidence buy signals right now.',
      metric: (s) => ({ text: formatConfidence(s.buy_confidence ?? s.confidence), className: 'text-emerald-600 dark:text-emerald-400' }),
    },
    {
      key: 'improved',
      title: 'Newly improved',
      caption: "Vs. today's opening signal",
      items: improved.map((x) => x.stock),
      emptyText: "No notable improvement since today's open.",
      metric: (s) => ({
        text: `+${Math.round((s.confidence - baseline[s.symbol]) * 100)}pt`,
        className: 'text-emerald-600 dark:text-emerald-400',
      }),
    },
    {
      key: 'weakened',
      title: 'Weakening signals',
      caption: "Vs. today's opening signal",
      items: weakened.map((x) => x.stock),
      emptyText: "Nothing weakening since today's open.",
      metric: (s) => ({
        text: `${Math.round((s.confidence - baseline[s.symbol]) * 100)}pt`,
        className: 'text-rose-600 dark:text-rose-400',
      }),
    },
    {
      key: 'sellrisk',
      title: 'Sell-risk warnings',
      caption: 'Highest downside risk',
      items: sellRisk,
      emptyText: 'No elevated downside risk detected.',
      metric: (s) => ({ text: formatConfidence(s.sell_confidence), className: 'text-rose-600 dark:text-rose-400' }),
    },
    {
      key: 'watchlist',
      title: 'Watchlist alerts',
      caption: 'Symbols you follow',
      items: watchlistAlerts,
      emptyText: watchlist.length ? 'No alerts on your watchlist.' : 'Star stocks to see alerts here.',
      metric: (s) => ({ text: formatConfidence(s.confidence) }),
    },
  ]

  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">Today's action board</h2>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {sections.map((section) => (
          <ActionBoardColumn key={section.key} section={section} />
        ))}
      </div>
    </div>
  )
}
