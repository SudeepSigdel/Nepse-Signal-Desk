import { useNavigate, useParams } from 'react-router-dom'
import { APP_TITLE } from '../config'
import { useSignal, useStockDetail } from '../hooks/useStocks'
import StockChart from './StockChart'

export default function StockDetailPage() {
  const { symbol = '' } = useParams()
  const navigate = useNavigate()
  const { detail, loading: detailLoading, error: detailError } = useStockDetail(symbol)
  const { signal, loading: signalLoading, error: signalError } = useSignal(symbol)

  const isLoading = detailLoading || signalLoading
  const error = detailError || signalError
  const latestClose = detail?.candles.at(-1)?.c ?? null
  const latestRsi = detail?.indicators.rsi.at(-1) ?? null
  const latestMacd = detail?.indicators.macd.at(-1) ?? null

  return (
    <div className="min-h-screen page-fade-in soft-grid pb-20">
      <nav className="sticky top-0 z-50 border-b border-white/10 bg-[#050505]/80 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center gap-4">
            <button 
              onClick={() => navigate('/')}
              className="p-2 -ml-2 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
              aria-label="Back to dashboard"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div className="h-4 w-[1px] bg-white/10 hidden sm:block"></div>
            <div className="font-display font-semibold text-white tracking-tight text-lg">
              {symbol.toUpperCase()} <span className="text-neutral-500 font-normal">| Research</span>
            </div>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 pt-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-200">
            <p className="font-medium">Error loading data</p>
            <p className="mt-1 text-sm opacity-80">{error}</p>
          </div>
        )}

        {isLoading ? (
          <div className="space-y-6">
            <DetailSkeleton />
          </div>
        ) : detail && (
          <div className="space-y-6">
            
            {/* Top Stats Row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 stagger-in">
              <MetricCard label="Latest Close" value={formatNumber(latestClose)} />
              <MetricCard label="RSI (14)" value={formatNumber(latestRsi)} />
              <MetricCard label="MACD" value={formatNumber(latestMacd)} />
              <MetricCard label="Data Points" value={detail.days.toString()} />
            </div>

            {/* AI Signal Analysis */}
            {signal && (
              <div className="glass-panel rounded-xl p-6 stagger-in">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                  
                  <div className="max-w-2xl">
                    <div className="flex items-center gap-3 mb-3">
                      <h2 className="text-lg font-semibold text-white">AI Analysis</h2>
                      <VerdictBadge verdict={signal.verdict} color={signal.verdict_color} />
                    </div>
                    
                    <p className="text-neutral-300 leading-relaxed">
                      {signal.description}
                    </p>

                    <div className="mt-5 flex flex-wrap gap-2">
                      <span className="chip-action text-xs">Date: {signal.date}</span>
                      <span className="chip-action text-xs">RSI: {signal.indicators.rsi_zone}</span>
                      <span className="chip-action text-xs">MACD: {signal.indicators.macd_bias}</span>
                      <span className="chip-action text-xs">{signal.indicators.volume_note}</span>
                    </div>
                  </div>

                  <div className="flex flex-col gap-4 md:min-w-[240px]">
                    <div className="glass-panel rounded-lg p-4 bg-black/20 border-white/5">
                      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-1">Confidence Score</div>
                      <div className="font-display text-4xl font-semibold text-white">
                        {(signal.confidence * 100).toFixed(1)}%
                      </div>
                    </div>

                    <div className="glass-panel rounded-lg p-4 bg-black/20 border-white/5">
                      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">Active Triggers</div>
                      <div className="flex flex-wrap gap-2">
                        {signal.active_signals.length > 0 ? (
                          signal.active_signals.map(item => (
                            <span key={item} className="inline-flex items-center px-2 py-1 rounded text-[10px] font-semibold bg-white/10 text-neutral-300">
                              {item}
                            </span>
                          ))
                        ) : (
                          <span className="text-sm text-neutral-500">None detected</span>
                        )}
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            )}

            {/* Charts */}
            <div className="stagger-in">
              <StockChart detail={detail} />
            </div>

          </div>
        )}
      </main>
    </div>
  )
}

function MetricCard({ label, value }: { label: string, value: string }) {
  return (
    <div className="glass-panel rounded-xl p-5">
      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">{label}</div>
      <div className="font-display text-2xl font-semibold text-white">{value}</div>
    </div>
  )
}

function VerdictBadge({ verdict, color }: { verdict: string, color: string }) {
  const colorMap: Record<string, string> = {
    green: 'bg-status-green text-status-green border-status-green/20',
    orange: 'bg-status-amber text-status-amber border-status-amber/20',
    red: 'bg-status-red text-status-red border-status-red/20',
    gray: 'bg-white/10 text-neutral-300 border-white/10',
  }
  
  const selectedClass = colorMap[color] || colorMap.gray
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider border ${selectedClass}`}>
      {verdict}
    </span>
  )
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-'
  }
  return value.toFixed(2)
}

function DetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="h-24 glass-panel rounded-xl" />
        <div className="h-24 glass-panel rounded-xl" />
        <div className="h-24 glass-panel rounded-xl" />
        <div className="h-24 glass-panel rounded-xl" />
      </div>
      <div className="h-48 glass-panel rounded-xl" />
      <div className="h-[400px] glass-panel rounded-xl" />
    </div>
  )
}
