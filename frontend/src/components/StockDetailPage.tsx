import React, { useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_BASE_URL } from '../config'
import axios from 'axios'
import { useSignal, useStockDetail } from '../hooks/useStocks'
import { useModelFamily } from '../modelFamily'
import ModelSelector from './ModelSelector'
import StockChart from './StockChart'
import { SignalCard } from './SignalCard'
import { PositionExitGuidance, type ExitStatus } from './PositionExitGuidance'
import { useTheme } from '../hooks/useTheme'

export default function StockDetailPage() {
  const { symbol = '' } = useParams()
  const navigate = useNavigate()
  const [familySelection, setFamilySelection] = useModelFamily()
  const { toggleTheme, isDark } = useTheme()
  const { detail, loading: detailLoading, error: detailError } = useStockDetail(symbol)
  const { signal, loading: signalLoading, error: signalError } = useSignal(symbol, familySelection)

  const [bothSignals, setBothSignals] = useState<{ xgboost?: any, random_forest?: any } | null>(null)

  React.useEffect(() => {
    let cancelled = false
    const fetchBoth = async () => {
      if (familySelection !== 'both') {
        setBothSignals(null)
        return
      }
      try {
        const resp = await axios.get(`${API_BASE_URL}/api/signal/${symbol}/both`)
        if (!cancelled) setBothSignals(resp.data)
      } catch (err) {
        console.error('Error fetching combined signals', err)
      }
    }
    fetchBoth()
    return () => { cancelled = true }
  }, [familySelection, symbol])
  
  // Position tracking state
  const [userEntryDate, setUserEntryDate] = useState('')
  const [userEntryPrice, setUserEntryPrice] = useState<number>(0)
  const [exitStatus, setExitStatus] = useState<ExitStatus | null>(null)
  const [exitLoading, setExitLoading] = useState(false)

  const isLoading = detailLoading || signalLoading
  const error = detailError || signalError
  const candles = detail?.candles ?? []
  const rsiValues = detail?.indicators.rsi ?? []
  const macdValues = detail?.indicators.macd ?? []
  const latestClose = candles.length > 0 ? candles[candles.length - 1]?.c ?? null : null
  const latestRsi = rsiValues.length > 0 ? rsiValues[rsiValues.length - 1] ?? null : null
  const latestMacd = macdValues.length > 0 ? macdValues[macdValues.length - 1] ?? null : null

  const checkExitStatus = useCallback(async () => {
    if (!userEntryDate || !userEntryPrice || !latestClose || !signal?.buy_confidence) return
    
    setExitLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/positions/exit-check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: symbol.toUpperCase(),
          entry_date: userEntryDate,
          entry_price: userEntryPrice,
          current_price: latestClose,
          current_buy_conf: signal.buy_confidence
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setExitStatus(data)
      } else {
        console.error('Failed to check exit status:', response.statusText)
      }
    } catch (err) {
      console.error('Error checking exit status:', err)
    } finally {
      setExitLoading(false)
    }
  }, [userEntryDate, userEntryPrice, latestClose, signal?.buy_confidence, symbol])

  // Check exit status when position details change
  React.useEffect(() => {
    if (userEntryDate && userEntryPrice && latestClose && signal?.buy_confidence) {
      checkExitStatus()
    }
  }, [checkExitStatus, userEntryDate, userEntryPrice, latestClose, signal?.buy_confidence])

  return (
    <div className="w-full min-h-screen page-fade-in soft-grid pb-20 bg-transparent">
      <nav className="sticky top-0 z-50 w-full border-b border-black/5 dark:border-white/10 bg-[var(--nav-bg)] backdrop-blur-md transition-colors duration-300">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center gap-4">
            <button 
              onClick={() => navigate('/')}
              className="-ml-2 rounded-full border border-black/8 dark:border-white/8 bg-black/[0.02] dark:bg-white/[0.02] p-2 text-slate-500 dark:text-neutral-300 transition hover:border-black/16 dark:hover:border-white/16 hover:bg-black/[0.06] dark:hover:bg-white/[0.06] hover:text-slate-900 dark:hover:text-white"
              aria-label="Back to dashboard"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div className="h-4 w-[1px] bg-black/10 dark:bg-white/10 hidden sm:block"></div>
            <div className="min-w-0 truncate font-display text-lg font-bold tracking-tight text-slate-900 dark:text-white">
              {symbol.toUpperCase()} <span className="font-normal text-slate-500 dark:text-neutral-400">Research</span>
            </div>
            
            <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
              <ModelSelector value={familySelection} onChange={setFamilySelection} />
              
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
        </div>
      </nav>

      <main className="mx-auto w-full max-w-7xl px-4 pt-8 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-red-200">
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
            <div className="grid grid-cols-2 gap-4 stagger-in lg:grid-cols-4">
              <MetricCard label="Latest Close" value={formatNumber(latestClose)} tooltip="Current stock price" />
              <MetricCard label="RSI (14)" value={formatNumber(latestRsi)} tooltip="Measures momentum: <30=Oversold, >70=Overbought" />
              <MetricCard label="MACD" value={formatNumber(latestMacd)} tooltip="Trend direction indicator" />
              <MetricCard label="Data Points" value={detail.days.toString()} tooltip="Number of trading days analyzed" />
            </div>

            {/* AI Signal Analysis */}
            {signal && (
              <SignalCard 
                verdict_color={signal.verdict_color}
                buy_confidence={signal.buy_confidence}
                sell_confidence={signal.sell_confidence}
                description={signal.description}
                active_signals={signal.active_signals}
                close={latestClose ?? undefined}
              />
            )}

            {familySelection === 'both' && bothSignals && (
              <div className="surface-panel p-4">
                <h4 className="section-kicker mb-3">Model comparison</h4>
                <div className="grid gap-3 sm:grid-cols-2">
                  {bothSignals.xgboost && (
                    <div className="comparison-tile">
                      <span>XGBoost buy</span>
                      <strong className="text-slate-900 dark:text-white">{(bothSignals.xgboost.buy_confidence * 100).toFixed(1)}%</strong>
                    </div>
                  )}
                  {bothSignals.random_forest && (
                    <div className="comparison-tile">
                      <span>Random Forest buy</span>
                      <strong className="text-slate-900 dark:text-white">{(bothSignals.random_forest.buy_confidence * 100).toFixed(1)}%</strong>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Your Position Input */}
            <div className="surface-panel p-5 stagger-in">
              <h3 className="mb-2 font-display text-xl font-bold tracking-tight text-slate-900 dark:text-white">
                Track your position
              </h3>
              <p className="mb-4 text-sm text-slate-500 dark:text-neutral-400">
                Enter your entry date and price to get exit guidance
              </p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div>
                  <label className="mb-2 block text-xs font-semibold text-slate-600 dark:text-neutral-400">
                    Entry Date
                  </label>
                  <input
                    type="date"
                    value={userEntryDate}
                    onChange={(e) => setUserEntryDate(e.target.value)}
                    className="control-field"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-xs font-semibold text-slate-600 dark:text-neutral-400">
                    Entry Price
                  </label>
                  <input
                    type="number"
                    placeholder="100.50"
                    value={userEntryPrice || ''}
                    onChange={(e) => setUserEntryPrice(parseFloat(e.target.value) || 0)}
                    className="control-field"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={checkExitStatus}
                    disabled={!userEntryDate || !userEntryPrice || exitLoading}
                    className="primary-action w-full disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {exitLoading ? '...' : 'Check Status'}
                  </button>
                </div>
              </div>
            </div>

            {/* Exit Guidance */}
            {exitStatus && (
              <PositionExitGuidance 
                status={exitStatus}
                onExit={() => {
                  setUserEntryDate('')
                  setUserEntryPrice(0)
                  setExitStatus(null)
                }}
              />
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

function MetricCard({ label, value, tooltip }: { label: string, value: string, tooltip?: string }) {
  const [showTooltip, setShowTooltip] = React.useState(false)
  
  return (
    <div 
      className="glass-panel relative cursor-help rounded-2xl p-5 group"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-neutral-500">{label}</div>
      <div className="font-display text-2xl font-bold tracking-tight text-slate-900 dark:text-white">{value}</div>
      
      {tooltip && showTooltip && (
        <div className="absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 whitespace-nowrap rounded-lg border border-black/10 dark:border-white/10 bg-slate-900 dark:bg-[#11151d] px-3 py-2 text-xs text-white dark:text-neutral-300 shadow-lg">
          {tooltip}
          <div className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-slate-900 dark:border-t-[#11151d]"></div>
        </div>
      )}
    </div>
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
