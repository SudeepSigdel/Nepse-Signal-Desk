import { Link } from 'react-router-dom'
import { useTheme } from '../../hooks/useTheme'
import { usePolling } from '../../hooks/usePolling'
import { fetchLiveAgents, fetchMarketBenchmark } from '../../lib/api'
import { formatDate, formatPercent } from '../../lib/format'
import type { PaperAccount } from '../../types'
import { agentColor } from '../agents/AgentEquityChart'

interface Row {
  key: string
  label: string
  value: number
  since: string | null
  color: string
  note?: string
}

/** "Did I beat the market / the bots?" - return since each one started, side by side. */
export function VersusCard({ account }: { account: PaperAccount }) {
  const { isDark } = useTheme()
  const { data: bench } = usePolling(() => fetchMarketBenchmark(account.id), [account.id])
  const { data: bots } = usePolling(fetchLiveAgents, [])

  const rows: Row[] = [
    { key: 'you', label: 'You', value: account.return_pct, since: account.created_at, color: isDark ? '#f4f4f5' : '#18181b' },
  ]
  if (bench) {
    rows.push({
      key: 'market',
      label: 'The market',
      value: bench.market_return_pct,
      since: bench.start_date,
      color: agentColor('BuyAndHold', isDark),
      note: `equal-weight, ${bench.stocks} liquid stocks, no fees`,
    })
  }
  for (const bot of bots ?? []) {
    rows.push({
      key: bot.name,
      label: bot.name,
      value: bot.account.return_pct,
      since: bot.account.created_at,
      color: agentColor(bot.name, isDark),
    })
  }
  const scale = Math.max(1, ...rows.map((r) => Math.abs(r.value)))

  let verdict = 'Your comparison appears after the first daily settlement.'
  if (bench && bench.start_date) {
    const gap = account.return_pct - bench.market_return_pct
    verdict =
      Math.abs(gap) < 0.05
        ? 'You are level with the market so far.'
        : gap > 0
          ? `You're ahead of the market by ${gap.toFixed(2)} points. Keep an eye on fees.`
          : `The market is ahead of you by ${Math.abs(gap).toFixed(2)} points. Most active traders trail the market after costs.`
  }

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">You vs the market and the bots</h2>
        <Link to="/agents" className="text-xs font-medium text-zinc-500 hover:underline dark:text-zinc-400">
          How the bots decide →
        </Link>
      </div>
      <ul className="mt-3 space-y-2.5">
        {rows.map((row) => (
          <li key={row.key} className="grid grid-cols-[7.5rem_1fr_4.5rem] items-center gap-3 text-sm">
            <span className="truncate text-zinc-700 dark:text-zinc-300">
              <span className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle" style={{ backgroundColor: row.color }} />
              {row.label}
            </span>
            <div className="relative h-2 rounded-full bg-zinc-100 dark:bg-zinc-800" title={row.note}>
              <div className="absolute inset-y-0 left-1/2 w-px bg-zinc-300 dark:bg-zinc-600" />
              <div
                className="absolute inset-y-0 rounded-full"
                style={{
                  backgroundColor: row.color,
                  left: row.value >= 0 ? '50%' : `${50 - (Math.abs(row.value) / scale) * 50}%`,
                  width: `${(Math.abs(row.value) / scale) * 50}%`,
                }}
              />
            </div>
            <span className="text-right tabular-nums text-zinc-900 dark:text-zinc-100">{formatPercent(row.value, { signed: true, digits: 2 })}</span>
            <span className="col-span-3 -mt-1.5 pl-[1.1rem] text-[11px] text-zinc-400 dark:text-zinc-500">
              since {formatDate(row.since)}
              {row.note ? ` · ${row.note}` : ''}
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-zinc-600 dark:text-zinc-400">{verdict}</p>
    </div>
  )
}
