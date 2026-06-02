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

export default function StockDetailPage() {
  const { symbol = '' } = useParams()
  const navigate = useNavigate()
  const [familySelection, setFamilySelection] = useModelFamily()
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
    <div className="w-full min-h-screen page-fade-in soft-grid pb-20">
      <nav className="w-full sticky top-0 z-50 border-b border-white/10 bg-[#050505]/80 backdrop-blur-md">
        <div className="w-full max-w-7xl pl-8 pr-4 md:pl-16 lg:pl-24">
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
            <div className="ml-auto hidden md:block">
              <ModelSelector value={familySelection} onChange={setFamilySelection} />
            </div>
          </div>
        </div>
      </nav>

      <main className="w-full max-w-7xl pl-8 pr-4 pt-8 md:pl-16 lg:pl-24">
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
                      <strong>{(bothSignals.xgboost.buy_confidence * 100).toFixed(1)}%</strong>
                    </div>
                  )}
                  {bothSignals.random_forest && (
                    <div className="comparison-tile">
                      <span>Random Forest buy</span>
                      <strong>{(bothSignals.random_forest.buy_confidence * 100).toFixed(1)}%</strong>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Your Position Input */}
            <div className="surface-panel p-5 stagger-in">
              <h3 className="mb-4 flex items-center gap-2 font-semibold text-white">
                💼 Track Your Position
              </h3>
              <p className="text-neutral-400 text-sm mb-4">
                Enter your entry date and price to get exit guidance
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-neutral-400 mb-2">
                    Entry Date
                  </label>
                  <input
                    type="date"
                    value={userEntryDate}
                    onChange={(e) => setUserEntryDate(e.target.value)}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-neutral-400 mb-2">
                    Entry Price
                  </label>
                  <input
                    type="number"
                    placeholder="100.50"
                    value={userEntryPrice || ''}
                    onChange={(e) => setUserEntryPrice(parseFloat(e.target.value) || 0)}
                    className="w-full bg-neutral-800 border border-neutral-700 rounded px-3 py-2 text-white placeholder-neutral-600 focus:outline-none focus:border-blue-500 transition"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={checkExitStatus}
                    disabled={!userEntryDate || !userEntryPrice || exitLoading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed text-white px-4 py-2 rounded font-semibold transition"
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
      className="glass-panel rounded-xl p-5 relative group cursor-help"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <div className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">{label}</div>
      <div className="font-display text-2xl font-semibold text-white">{value}</div>
      
      {tooltip && showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-neutral-900 border border-neutral-700 rounded-lg text-xs text-neutral-300 whitespace-nowrap z-10 shadow-lg">
          {tooltip}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-neutral-900"></div>
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
