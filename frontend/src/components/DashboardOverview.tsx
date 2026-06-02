import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { APP_TITLE, REFRESH_INTERVAL_MS } from '../config'
import { useStocks, type Stock } from '../hooks/useStocks'
import { useModelFamily, type ModelFamily } from '../modelFamily'
import ModelSelector from './ModelSelector'
import { GlossaryModal } from './GlossaryModal'
import { RiskPanel } from './RiskPanel'
import { useTheme } from '../hooks/useTheme'

type VerdictFilter = 'all' | 'BUY' | 'MODERATE' | 'SELL' | 'WEAK_SELL' | 'HOLD' | 'AVOID'

const verdictFilters: Array<{ label: string; value: VerdictFilter }> = [
  { label: 'All', value: 'all' },
  { label: 'Buy', value: 'BUY' },
  { label: 'Watch', value: 'MODERATE' },
  { label: 'Sell risk', value: 'SELL' },
  { label: 'Soft risk', value: 'WEAK_SELL' },
  { label: 'Hold', value: 'HOLD' },
  { label: 'Avoid', value: 'AVOID' },
]

function primaryConfidence(stock: Stock) {
  return stock.confidence ?? stock.buy_confidence ?? 0
}

function deriveVerdict(stock: Stock): VerdictFilter {
  if (stock.verdict === 'BUY' || stock.verdict === 'MODERATE' || stock.verdict === 'SELL' || stock.verdict === 'WEAK_SELL' || stock.verdict === 'HOLD' || stock.verdict === 'AVOID') {
    return stock.verdict
  }
  const buy = primaryConfidence(stock)
  if (buy >= 0.65) return 'BUY'
  if (buy >= 0.55) return 'MODERATE'
  if (stock.sell_confidence && stock.sell_confidence >= 0.65) return 'SELL'
  if (stock.sell_confidence && stock.sell_confidence >= 0.55) return 'WEAK_SELL'
  if (buy >= 0.45) return 'HOLD'
  return 'AVOID'
}

export default function DashboardOverview() {
  const { toggleTheme, isDark } = useTheme()
  const [family, setFamily] = useModelFamily()
  const { stocks, loading, error } = useStocks(REFRESH_INTERVAL_MS, family)
  const [searchTerm, setSearchTerm] = useState('')
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>('all')
  const navigate = useNavigate()

  const enrichedStocks = useMemo(
    () => stocks.map((stock) => ({ ...stock, verdict: deriveVerdict(stock) })),
    [stocks]
  )

  const filteredStocks = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    return enrichedStocks.filter((stock) => {
      const matchesSearch =
        !query ||
        stock.symbol.toLowerCase().includes(query) ||
        stock.tier.toLowerCase().includes(query) ||
        (stock.verdict ?? '').toLowerCase().includes(query)

      const matchesVerdict = verdictFilter === 'all' || stock.verdict === verdictFilter
      return matchesSearch && matchesVerdict
    })
  }, [enrichedStocks, searchTerm, verdictFilter])

  const sortedStocks = useMemo(
    () => [...filteredStocks].sort((left, right) => primaryConfidence(right) - primaryConfidence(left)),
    [filteredStocks]
  )

  const topSignal = sortedStocks[0]
  const buyCount = enrichedStocks.filter((stock) => stock.verdict === 'BUY').length
  const watchCount = enrichedStocks.filter((stock) => stock.verdict === 'MODERATE').length
  const riskCount = enrichedStocks.filter((stock) => stock.verdict === 'SELL' || stock.verdict === 'WEAK_SELL').length
  const refreshSeconds = Math.round(REFRESH_INTERVAL_MS / 1000)

  return (
    <div className="min-h-screen w-full bg-transparent page-fade-in pb-12">
      <TopNav
        family={family}
        setFamily={setFamily}
        refreshSeconds={refreshSeconds}
        isDark={isDark}
        toggleTheme={toggleTheme}
      />

      <main className="mx-auto w-full max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-4 rounded-lg border border-red-400/30 bg-red-950/40 p-4 text-red-100">
            <p className="text-sm font-semibold">Connection problem</p>
            <p className="mt-1 text-sm text-red-100/75">
              {error === 'Network Error' || error.includes('Network')
                ? 'Backend is not reachable. Start the API server and refresh.'
                : error}
            </p>
          </div>
        )}

        <section className="market-header">
          <div>
            <p className="section-kicker">NEPSE signal board</p>
            <h1 className="mt-2 font-display text-3xl font-semibold text-slate-900 dark:text-white sm:text-4xl">Market Overview</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
              Liquid, model-ready stocks ranked by current 10-day opportunity score.
            </p>
          </div>

          <div className="market-header-panel">
            <StatTile label="Universe" value={enrichedStocks.length.toString()} tone="blue" />
            <StatTile label="Buy" value={buyCount.toString()} tone="green" />
            <StatTile label="Watch" value={watchCount.toString()} tone="amber" />
            <StatTile label="Risk" value={riskCount.toString()} tone="red" />
          </div>
        </section>

        <section className="mt-5 grid gap-4 lg:grid-cols-[280px_1fr]">
          <aside className="space-y-4">
            <div className="surface-panel p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="section-kicker">Controls</p>
                <span className="live-pill">Live {refreshSeconds}s</span>
              </div>
              <div className="mt-4 space-y-4">
                <ModelSelector value={family} onChange={setFamily} />
                <div>
                  <label htmlFor="stock-search" className="mb-2 block text-xs font-semibold text-slate-500 dark:text-slate-400">
                    Symbol or verdict
                  </label>
                  <input
                    id="stock-search"
                    type="text"
                    value={searchTerm}
                    onChange={(event) => setSearchTerm(event.target.value)}
                    placeholder="Search NABIL, BUY..."
                    className="control-field"
                  />
                </div>
              </div>
            </div>

            {topSignal && (
              <div className="surface-panel p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="section-kicker">Top of tape</p>
                    <div className="mt-3 font-display text-4xl font-semibold text-slate-900 dark:text-white">{topSignal.symbol}</div>
                  </div>
                  <VerdictBadge verdict={topSignal.verdict ?? 'HOLD'} />
                </div>
                <div className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                  <SignalMeter label="Score" value={primaryConfidence(topSignal)} verdict={topSignal.verdict ?? 'HOLD'} />
                  {topSignal.sell_confidence !== null && topSignal.sell_confidence !== undefined && (
                    <SignalMeter label="Sell risk" value={topSignal.sell_confidence} verdict="SELL" />
                  )}
                </div>
                <button onClick={() => navigate(`/stocks/${topSignal.symbol}`)} className="primary-action mt-5 w-full">
                  Open research
                </button>
              </div>
            )}

            <div className="surface-panel p-4">
              <p className="section-kicker">Filter</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {verdictFilters.map((filter) => (
                  <button
                    key={filter.value}
                    onClick={() => setVerdictFilter(filter.value)}
                    className={verdictFilter === filter.value ? 'chip-action chip-action-active' : 'chip-action'}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <section className="surface-panel overflow-hidden">
            <div className="flex flex-col gap-3 border-b border-white/10 px-4 py-4 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="section-kicker">Ranked universe</p>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Showing {sortedStocks.length} of {enrichedStocks.length} liquid symbols
                </p>
              </div>
            </div>

            {loading ? (
              <div className="grid gap-3 p-4">
                {Array.from({ length: 8 }).map((_, index) => (
                  <div key={index} className="h-12 animate-pulse rounded bg-slate-200 dark:bg-white/[0.04]" />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto subtle-scrollbar">
                <table className="market-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th className="text-right">Close</th>
                      <th className="text-right">RSI</th>
                      <th className="text-right">{family === 'both' ? 'Blend' : 'Buy score'}</th>
                      {family === 'both' && <th className="text-right">XGB</th>}
                      {family === 'both' && <th className="text-right">RF</th>}
                      <th className="text-right">Sell risk</th>
                      <th>Status</th>
                      <th>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedStocks.length === 0 ? (
                      <tr>
                        <td colSpan={family === 'both' ? 9 : 7} className="py-12 text-center text-slate-500">
                          No symbols match the current filters.
                        </td>
                      </tr>
                    ) : (
                      sortedStocks.map((stock) => (
                        <tr key={stock.symbol} onClick={() => navigate(`/stocks/${stock.symbol}`)}>
                          <td>
                            <span className="font-semibold text-slate-900 dark:text-white">{stock.symbol}</span>
                          </td>
                          <td className="text-right tabular-nums">{stock.close.toFixed(2)}</td>
                          <td className="text-right tabular-nums">{stock.rsi !== null ? stock.rsi.toFixed(1) : '-'}</td>
                          <td className="min-w-36 text-right">
                            <SignalMeter value={primaryConfidence(stock)} verdict={stock.verdict ?? 'HOLD'} compact />
                          </td>
                          {family === 'both' && (
                            <td className="text-right tabular-nums">{formatPercent(stock.buy_confidence)}</td>
                          )}
                          {family === 'both' && (
                            <td className="text-right tabular-nums">{formatPercent(stock.rf_confidence)}</td>
                          )}
                          <td className="text-right tabular-nums">{formatPercent(stock.sell_confidence)}</td>
                          <td><VerdictBadge verdict={stock.verdict ?? 'HOLD'} /></td>
                          <td className="text-slate-500 dark:text-slate-500">{stock.date}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </section>

        <section className="mt-6">
          <RiskPanel />
        </section>

        <GlossaryModal />
      </main>
    </div>
  )
}

function TopNav({
  family,
  setFamily,
  refreshSeconds,
  isDark,
  toggleTheme,
}: {
  family: ModelFamily
  setFamily: (family: ModelFamily) => void
  refreshSeconds: number
  isDark: boolean
  toggleTheme: () => void
}) {
  return (
    <nav className="sticky top-0 z-50 border-b border-black/5 dark:border-white/10 bg-[var(--nav-bg)] backdrop-blur-md transition-colors duration-300">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-2 px-4 sm:gap-4 sm:px-6 lg:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-md">
            <span className="text-white font-display font-bold text-sm">N</span>
          </div>
          <div className="min-w-0">
            <p className="truncate font-display text-base font-bold text-slate-900 dark:text-white tracking-tight">{APP_TITLE}</p>
            <p className="hidden text-[10px] text-slate-500 sm:block">Refreshes every {refreshSeconds}s</p>
          </div>
        </div>
        
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <ModelSelector value={family} onChange={setFamily} />
          
          <button
            onClick={toggleTheme}
            type="button"
            className="p-2 rounded-xl border border-black/10 dark:border-white/10 bg-black/[0.02] dark:bg-white/[0.02] text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-black/[0.06] dark:hover:bg-white/[0.06] transition-all"
            aria-label="Toggle theme"
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          >
            {isDark ? (
              <svg className="w-5 h-5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 9h-1m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </nav>
  )
}

function StatTile({ label, value, tone }: { label: string; value: string; tone: 'blue' | 'green' | 'amber' | 'red' }) {
  return (
    <div className={`stat-tile stat-tile-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function SignalMeter({
  label,
  value,
  verdict,
  compact = false,
}: {
  label?: string
  value: number | null | undefined
  verdict: string
  compact?: boolean
}) {
  const width = Math.max(0, Math.min(100, (value ?? 0) * 100))
  return (
    <div className={compact ? 'signal-meter signal-meter-compact' : 'signal-meter'}>
      {label && <span className="text-slate-400">{label}</span>}
      <div className="signal-meter-track">
        <div className="signal-meter-fill" data-verdict={verdict} style={{ width: `${width}%` }} />
      </div>
      <strong>{formatPercent(value)}</strong>
    </div>
  )
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const normalized = verdict === 'WEAK_SELL' ? 'WEAK_SELL' : verdict
  const label =
    normalized === 'BUY' ? 'Buy' :
    normalized === 'MODERATE' ? 'Watch' :
    normalized === 'SELL' ? 'Sell risk' :
    normalized === 'WEAK_SELL' ? 'Soft risk' :
    normalized === 'AVOID' ? 'Avoid' :
    'Hold'

  return <span className="verdict-badge" data-verdict={normalized}>{label}</span>
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-'
  }
  return `${(value * 100).toFixed(1)}%`
}
