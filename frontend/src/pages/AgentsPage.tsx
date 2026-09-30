import { Bot, FlaskConical } from 'lucide-react'
import { useEffect } from 'react'
import { AgentEquityChart, agentColor } from '../components/agents/AgentEquityChart'
import { PaperDisclaimer } from '../components/paper/PaperDisclaimer'
import { EmptyState } from '../components/ui/EmptyState'
import { useTheme } from '../hooks/useTheme'
import { usePolling } from '../hooks/usePolling'
import { fetchAgentReport, fetchLiveAgents } from '../lib/api'
import { markVisitedAgents } from '../lib/onboarding'
import { formatDate, formatMoney, formatPercent } from '../lib/format'
import type { AgentComparison, AgentEntry, AgentReport } from '../types'

const cardClass = 'rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900'
const thClass = 'px-2 py-1.5 text-left text-[11px] font-medium text-zinc-400 dark:text-zinc-500'
const tdClass = 'px-2 py-1.5 tabular-nums text-zinc-700 dark:text-zinc-300'

function tone(value: number | null | undefined) {
  if (value === null || value === undefined || value === 0) return ''
  return value > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
}

function Swatch({ name }: { name: string }) {
  const { isDark } = useTheme()
  return <span className="mr-1.5 inline-block h-2 w-2 rounded-full align-middle" style={{ backgroundColor: agentColor(name, isDark) }} />
}

function Headline({ report }: { report: AgentReport }) {
  const byName = Object.fromEntries(report.agents.map((a) => [a.name, a]))
  const tuned = byName.TunedSignalBot?.metrics
  const market = byName.BuyAndHold?.metrics
  const random = byName.RandomBot?.metrics
  if (!tuned || !market) return null
  const beatMarket = tuned.total_return_pct > market.total_return_pct
  return (
    <div className={`${cardClass} space-y-2 text-sm text-zinc-700 dark:text-zinc-300`}>
      <h2 className="flex items-center gap-1.5 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
        <FlaskConical className="h-4 w-4" /> What the experiment found
      </h2>
      <p>
        From {formatDate(report.period.start)} to {formatDate(report.period.end)}, trading only on predictions the model made
        for years it had never seen, the tuned model bot returned{' '}
        <strong className={tone(tuned.total_return_pct)}>{formatPercent(tuned.total_return_pct, { signed: true })}</strong>{' '}
        while simply buying the market returned{' '}
        <strong className={tone(market.total_return_pct)}>{formatPercent(market.total_return_pct, { signed: true })}</strong>.
        {beatMarket ? ' The model beat the market here.' : ' Picking stocks with the model did not beat holding the market.'}
      </p>
      <p>
        It did cut the worst drop to {formatPercent(tuned.max_drawdown_pct)} (market: {formatPercent(market.max_drawdown_pct)}) and
        clearly beat random picks{random ? ` (${formatPercent(random.total_return_pct, { signed: true })})` : ''}, but it paid{' '}
        {formatMoney(tuned.fees_paid)} in fees and tax on {formatMoney(report.starting_cash)} of capital. Short-term trading on NEPSE
        is expensive: every round trip costs about 1% before any capital gains tax.
      </p>
    </div>
  )
}

function MetricsTable({ agents }: { agents: AgentEntry[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            {['Agent', 'Return', 'Per year', 'Sharpe', 'Worst drop', 'Invested', 'Trades', 'Win rate', 'Fees & tax'].map((h) => (
              <th key={h} className={thClass}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => (
            <tr key={a.name} className="border-t border-zinc-100 dark:border-zinc-800">
              <td className={`${tdClass} whitespace-nowrap font-medium`}>
                <Swatch name={a.name} />
                {a.name}
              </td>
              <td className={`${tdClass} ${tone(a.metrics.total_return_pct)}`}>{formatPercent(a.metrics.total_return_pct, { signed: true })}</td>
              <td className={tdClass}>{formatPercent(a.metrics.cagr_pct, { signed: true })}</td>
              <td className={tdClass}>{a.metrics.sharpe.toFixed(2)}</td>
              <td className={tdClass}>{formatPercent(a.metrics.max_drawdown_pct)}</td>
              <td className={tdClass}>{formatPercent(a.metrics.avg_exposure_pct ?? null, { digits: 0 })}</td>
              <td className={tdClass}>{a.metrics.trades}</td>
              <td className={tdClass}>{a.metrics.win_rate_pct != null ? formatPercent(a.metrics.win_rate_pct, { digits: 0 }) : '—'}</td>
              <td className={tdClass}>{formatMoney(a.metrics.fees_paid)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function YearTable({ agents }: { agents: AgentEntry[] }) {
  const years = Array.from(new Set(agents.flatMap((a) => a.per_fold.map((f) => f.year)))).sort()
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className={thClass}>Agent</th>
            {years.map((y) => (
              <th key={y} className={`${thClass} text-right`}>
                {y}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => {
            const byYear = Object.fromEntries(a.per_fold.map((f) => [f.year, f.return_pct]))
            return (
              <tr key={a.name} className="border-t border-zinc-100 dark:border-zinc-800">
                <td className={`${tdClass} whitespace-nowrap`}>
                  <Swatch name={a.name} />
                  {a.name}
                </td>
                {years.map((y) => (
                  <td key={y} className={`${tdClass} text-right ${tone(byYear[y])}`}>
                    {byYear[y] !== undefined ? formatPercent(byYear[y], { signed: true, digits: 0 }) : '—'}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function Comparison({ c }: { c: AgentComparison }) {
  const better = c.annualized_diff_pct >= 0
  return (
    <li className="text-xs text-zinc-600 dark:text-zinc-400">
      <span className="font-medium text-zinc-800 dark:text-zinc-200">{c.a}</span> vs {c.b}: about{' '}
      <span className={tone(c.annualized_diff_pct)}>{formatPercent(c.annualized_diff_pct, { signed: true })}/yr</span>{' '}
      {better ? 'better' : 'worse'}.{' '}
      {c.significant ? (
        <span className="font-medium">Statistically clear</span>
      ) : (
        <span>Not statistically clear: it could be luck</span>
      )}{' '}
      (95% CI of the daily difference {c.ci_pct[0].toFixed(3)}% to {c.ci_pct[1].toFixed(3)}%).
    </li>
  )
}

function LiveBots() {
  const { data, error } = usePolling(fetchLiveAgents, [])
  if (error) return <p className="text-xs text-zinc-400">Live bot accounts are unavailable right now.</p>
  if (!data || data.length === 0)
    return <p className="text-xs text-zinc-400 dark:text-zinc-500">The bots start trading after the next daily pipeline run.</p>
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data.map((bot) => (
        <div key={bot.name} className={cardClass}>
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              <Swatch name={bot.name} />
              {bot.name}
            </h3>
            <span className={`text-sm font-semibold tabular-nums ${tone(bot.account.return_pct)}`}>
              {formatPercent(bot.account.return_pct, { signed: true, digits: 2 })}
            </span>
          </div>
          <p className="mt-0.5 text-[11px] text-zinc-400 dark:text-zinc-500">
            Equity {formatMoney(bot.account.equity)} · {bot.account.positions.length} positions
            {bot.settings ? ` · ${bot.settings}` : ''}
          </p>
          <ul className="mt-3 space-y-1.5">
            {bot.recent_orders.slice(0, 6).map((o) => (
              <li key={o.id} className="text-xs text-zinc-600 dark:text-zinc-400">
                <span className={`font-medium uppercase ${o.side === 'buy' ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'}`}>
                  {o.side}
                </span>{' '}
                {o.qty} {o.symbol} <span className="text-zinc-400">({o.status})</span>
                {o.note && <span className="block text-[11px] text-zinc-400 dark:text-zinc-500">{o.note}</span>}
              </li>
            ))}
            {bot.recent_orders.length === 0 && <li className="text-xs text-zinc-400">No orders yet.</li>}
          </ul>
        </div>
      ))}
    </div>
  )
}

export function AgentsPage() {
  const { data: report, error } = usePolling(() => fetchAgentReport('xgboost'), [])
  useEffect(() => {
    markVisitedAgents()
  }, [])

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Trading agents</h1>
        <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
          Bots that trade with the same virtual money, prices, fees and rules as you, and an honest test of whether they work.
        </p>
      </div>
      <PaperDisclaimer />

      <section className="space-y-2">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Live bots</h2>
        <LiveBots />
      </section>

      {error ? (
        <EmptyState icon={Bot} title="No agent report yet" description="It is generated by the daily pipeline (src/09_agent_backtest.py)." />
      ) : !report ? (
        <p className="text-sm text-zinc-400">Loading report…</p>
      ) : (
        <>
          <Headline report={report} />

          <div className={cardClass}>
            <h2 className="mb-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
              Rs {(report.starting_cash / 100000).toFixed(0)} lakh, traded by each agent
            </h2>
            <p className="mb-3 text-[11px] text-zinc-400 dark:text-zinc-500">Weekly equity, after all fees and taxes. Dashed: buy and hold the market.</p>
            <AgentEquityChart agents={report.agents} startingCash={report.starting_cash} />
          </div>

          <div className={cardClass}>
            <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Scorecard</h2>
            <MetricsTable agents={report.agents} />
            <ul className="mt-3 space-y-1.5">
              {report.agents.map((a) => (
                <li key={a.name} className="text-xs text-zinc-500 dark:text-zinc-400">
                  <Swatch name={a.name} />
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">{a.name}:</span> {a.description}
                </li>
              ))}
            </ul>
          </div>

          <div className={cardClass}>
            <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Year by year</h2>
            <YearTable agents={report.agents} />
          </div>

          <div className={cardClass}>
            <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Is the difference real?</h2>
            <ul className="space-y-1.5">
              {report.comparisons.map((c) => (
                <Comparison key={`${c.a}-${c.b}`} c={c} />
              ))}
            </ul>
          </div>

          {report.rl && (
            <div className={cardClass}>
              <h2 className="mb-1 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Reinforcement-learning bot (research)</h2>
              <p className="mb-2 text-xs text-zinc-500 dark:text-zinc-400">
                Each day it chooses one of: {report.rl.allocations.join(' · ')}. Trained on 4 past years, tested on the next unseen year,{' '}
                {formatDate(report.rl.window.start)} to {formatDate(report.rl.window.end)}.
              </p>
              <MetricsTable agents={report.rl.agents} />
              <p className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
                <span className="font-medium">{report.rl.promoted ? 'Promoted to live trading.' : 'Not promoted to live trading.'}</span>{' '}
                {report.rl.promotion_reason}
              </p>
            </div>
          )}

          <div className={`${cardClass} text-xs text-zinc-500 dark:text-zinc-400`}>
            <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">How this was tested</h2>
            <ul className="list-disc space-y-1 pl-4">
              {Object.values(report.method).map((line) => (
                <li key={line}>{line}</li>
              ))}
              <li>
                {report.data_notes.explanation} ({report.data_notes.corporate_action_gaps_adjusted} adjustments.)
              </li>
              <li>
                TunedSignalBot's yearly settings:{' '}
                {report.tuning.map((t) => `${t.test_start.slice(0, 4)}: ${t.label}`).join('; ')}.
              </li>
            </ul>
          </div>
        </>
      )}
    </div>
  )
}
