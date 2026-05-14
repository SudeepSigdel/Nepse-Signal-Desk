import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { APP_TITLE, REFRESH_INTERVAL_MS } from '../config'
import { useStocks } from '../hooks/useStocks'
import { GlossaryModal } from './GlossaryModal'
import { RiskPanel } from './RiskPanel'

type VerdictFilter = 'all' | 'BUY' | 'MODERATE' | 'SELL' | 'WEAK_SELL' | 'HOLD'

// Compute verdict from dual confidence scores
function getVerdict(buy_confidence: number, sell_confidence?: number | null): VerdictFilter {
  if (buy_confidence >= 0.65) return 'BUY'
  if (buy_confidence >= 0.55) return 'MODERATE'
  if (sell_confidence && sell_confidence >= 0.65) return 'SELL'
  if (sell_confidence && sell_confidence >= 0.55) return 'WEAK_SELL'
  return 'HOLD'
}

export default function DashboardOverview() {
  const { stocks, loading, error } = useStocks()
  const [searchTerm, setSearchTerm] = useState('')
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>('all')
  const navigate = useNavigate()

  // Enrich stocks with computed verdict
  const enrichedStocks = stocks.map((stock) => ({
    ...stock,
    verdict: getVerdict(stock.buy_confidence ?? stock.confidence, stock.sell_confidence),
  }))

  const filteredStocks = enrichedStocks.filter((stock) => {
    const matchesSearch =
      stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      stock.verdict.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesVerdict =
      verdictFilter === 'all' || stock.verdict === verdictFilter

    return matchesSearch && matchesVerdict
  })

  const sortedStocks = [...filteredStocks].sort((left, right) => 
    (right.buy_confidence ?? right.confidence) - (left.buy_confidence ?? left.confidence)
  )
  const topSignal = sortedStocks[0]
  
  const buyCount = filteredStocks.filter((stock) => stock.verdict === 'BUY').length
  const moderateCount = filteredStocks.filter((stock) => stock.verdict === 'MODERATE').length
  const sellCount = filteredStocks.filter((stock) => stock.verdict === 'SELL').length

  const verdictFilters: Array<{ label: string; value: VerdictFilter }> = [
    { label: 'All', value: 'all' },
    { label: '🟢 BUY', value: 'BUY' },
    { label: '🟠 MODERATE', value: 'MODERATE' },
    { label: '🔴 SELL', value: 'SELL' },
    { label: '🟡 WEAK SELL', value: 'WEAK_SELL' },
    { label: '⚪ HOLD', value: 'HOLD' },
  ]

  return (
    <div className="w-full min-h-screen page-fade-in soft-grid pb-20">
      <TopNav />
      
      <main className="w-full max-w-7xl pl-8 pr-4 pt-8 md:pl-16 lg:pl-24">
        
        {/* Error State */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-500/20 bg-red-500/10 p-4 text-red-200">
            <p className="font-medium">Connection Error</p>
            <p className="mt-1 text-sm opacity-80">
              {error === 'Network Error' || error.includes('Network') 
                ? 'Could not connect to the server. Please ensure the backend server is running.' 
                : error}
            </p>
          </div>
        )}

        <div className="mb-8 flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Market Overview
            </h1>
            <p className="mt-2 text-sm text-neutral-400 max-w-xl">
              Screen and analyze NEPSE opportunities with AI-driven confidence scores and momentum indicators.
            </p>
          </div>
          
          <div className="flex w-full flex-col gap-3 md:w-auto md:flex-row md:items-center">
            <div className="relative w-full md:w-64">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search symbol..."
                className="control-field pl-9"
              />
            </div>
            
            <div className="flex gap-2 overflow-x-auto pb-1 md:pb-0 subtle-scrollbar">
              {verdictFilters.map((filter) => (
                <button
                  key={filter.value}
                  onClick={() => setVerdictFilter(filter.value)}
                  className={`chip-action whitespace-nowrap ${verdictFilter === filter.value ? 'chip-action-active' : ''}`}
                >
                  {filter.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="grid gap-6 md:grid-cols-3">
            <DashboardSkeleton />
            <DashboardSkeleton />
            <DashboardSkeleton />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="grid gap-6 lg:grid-cols-4">
              
              {/* Left Column: KPIs & Top Signal */}
              <div className="space-y-6 lg:col-span-1">
                <div className="glass-panel rounded-xl p-5 stagger-in">
                  <h3 className="section-kicker mb-4">Summary</h3>
                  <div className="space-y-4">
                    <KpiRow label="Total Signals " value={filteredStocks.length} />
                    <KpiRow label="🟢 BUY " value={buyCount} highlight="green" />
                    <KpiRow label="🟠 MODERATE " value={moderateCount} highlight="amber" />
                    <KpiRow label="🔴 SELL " value={sellCount} highlight="red" />
                  </div>
                </div>

                {topSignal && (
                  <div className="glass-panel rounded-xl p-5 stagger-in flex flex-col">
                    <div className="flex justify-between items-start mb-4">
                      <h3 className="section-kicker">Top Signal</h3>
                      <VerdictBadge verdict={topSignal.verdict} />
                    </div>
                    
                    <div className="mb-6">
                      <div className="font-display text-4xl font-semibold text-white mb-1">
                        {topSignal.symbol}
                      </div>
                      <div className="text-sm text-neutral-400">
                        <div>BUY Confidence: <span className="text-white font-medium">{((topSignal.buy_confidence ?? topSignal.confidence) * 100).toFixed(1)}%</span></div>
                        {topSignal.sell_confidence && (
                          <div>SELL Confidence: <span className="text-white font-medium">{(topSignal.sell_confidence * 100).toFixed(1)}%</span></div>
                        )}
                      </div>
                    </div>

                    <button 
                      onClick={() => navigate(`/stocks/${topSignal.symbol}`)}
                      className="primary-action w-full mt-auto"
                    >
                      Analyze
                    </button>
                  </div>
                )}
              </div>

              {/* Right Column: Data Grid */}
              <div className="lg:col-span-3">
                <div className="glass-panel rounded-xl overflow-hidden stagger-in flex flex-col h-full">
                  <div className="overflow-x-auto subtle-scrollbar">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-white/10 bg-white/[0.02]">
                          <th className="px-5 py-4 text-xs font-semibold uppercase tracking-wider text-neutral-400">Symbol</th>
                          <th className="px-5 py-4 text-xs font-semibold uppercase tracking-wider text-neutral-400 text-right">Close</th>
                          <th className="px-5 py-4 text-xs font-semibold uppercase tracking-wider text-neutral-400 text-right">
                            <span title="Relative Strength Index: Measures momentum">RSI ℹ️</span>
                          </th>
                          <th className="px-5 py-4 text-xs font-semibold uppercase tracking-wider text-neutral-400 text-right">
                            <span title="How confident the AI is in this signal (higher is better)">Confidence ℹ️</span>
                          </th>
                          <th className="px-5 py-4 text-xs font-semibold uppercase tracking-wider text-neutral-400 text-center">Signal Strength</th>
                          <th className="px-5 py-4 text-xs font-semibold uppercase tracking-wider text-neutral-400">Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {filteredStocks.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-5 py-12 text-center text-neutral-500">
                              No signals match your current filters.
                            </td>
                          </tr>
                        ) : (
                          filteredStocks.map((stock) => (
                            <tr 
                              key={stock.symbol}
                              onClick={() => navigate(`/stocks/${stock.symbol}`)}
                              className="group cursor-pointer transition-colors hover:bg-white/[0.04]"
                            >
                              <td className="px-5 py-4 whitespace-nowrap">
                                <div className="font-medium text-white group-hover:text-blue-400 transition-colors">
                                  {stock.symbol}
                                </div>
                              </td>
                              <td className="px-5 py-4 whitespace-nowrap text-right text-neutral-300 tabular-nums">
                                {stock.close.toFixed(2)}
                              </td>
                              <td className="px-5 py-4 whitespace-nowrap text-right text-neutral-300 tabular-nums">
                                {stock.rsi !== null ? stock.rsi.toFixed(1) : '-'}
                              </td>
                              <td className="px-5 py-4 whitespace-nowrap text-right tabular-nums">
                                <div className="flex items-center justify-end gap-2">
                                  <div className="w-16 h-1.5 bg-neutral-800 rounded-full overflow-hidden hidden sm:block">
                                    <div 
                                      className="h-full rounded-full bg-blue-500" 
                                      style={{ width: `${Math.min(100, (stock.buy_confidence ?? stock.confidence) * 100)}%`, backgroundColor: getVerdictColor(stock.verdict) }}
                                    />
                                  </div>
                                  <span className="text-white font-medium">
                                    {((stock.buy_confidence ?? stock.confidence) * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </td>
                              <td className="px-5 py-4 whitespace-nowrap text-center">
                                 <VerdictBadge verdict={stock.verdict} />
                              </td>
                              <td className="px-5 py-4 whitespace-nowrap text-sm text-neutral-500">
                                {stock.date}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>

            {/* Risk Management & Disclaimers Section */}
            <div className="mt-8 pt-8 border-t border-white/10">
              <h2 className="text-2xl font-semibold text-white mb-6">Risk Management & Disclaimers</h2>
              <RiskPanel />
            </div>
          </div>
        )}

        {/* Glossary Modal */}
        <GlossaryModal />
      </main>
    </div>
  )
}

function TopNav() {
  const refreshSeconds = Math.round(REFRESH_INTERVAL_MS / 1000)
  
  return (
    <nav className="w-full sticky top-0 z-50 border-b border-white/10 bg-[#050505]/80 backdrop-blur-md">
      <div className="w-full max-w-7xl pl-8 pr-4 md:pl-16 lg:pl-24">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center">
            <span className="font-display font-semibold text-white tracking-tight">
              {APP_TITLE}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 text-xs font-medium text-neutral-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Auto-updating ({refreshSeconds}s)
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}

function DashboardSkeleton() {
  return (
    <div className="glass-panel rounded-xl p-5 animate-pulse">
      <div className="h-4 w-24 bg-white/10 rounded mb-4" />
      <div className="space-y-3">
        <div className="h-10 bg-white/5 rounded" />
        <div className="h-10 bg-white/5 rounded" />
        <div className="h-10 bg-white/5 rounded" />
      </div>
    </div>
  )
}

function KpiRow({ label, value, highlight }: { label: string, value: number, highlight?: 'green' | 'amber' | 'red' }) {
  const colorClass = 
    highlight === 'green' ? 'text-emerald-400' :
    highlight === 'amber' ? 'text-amber-400' :
    highlight === 'red' ? 'text-red-400' :
    'text-white'
  
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-neutral-400">{label}</span>
      <span className={`font-medium tabular-nums ${colorClass}`}>
        {value}
      </span>
    </div>
  )
}

function TierBadge({ tier }: { tier: string }) {
  if (tier === 'High') return <span className="inline-flex items-center px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-status-green text-status-green border">High</span>
  if (tier === 'Medium') return <span className="inline-flex items-center px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-status-amber text-status-amber border">Medium</span>
  return <span className="inline-flex items-center px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-white/10 text-neutral-300 border border-white/10">Low/Neutral</span>
}

function VerdictBadge({ verdict }: { verdict: string }) {
  switch (verdict) {
    case 'BUY':
      return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-400/30">🟢 BUY</span>
    case 'MODERATE':
      return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-400/30">🟠 MOD</span>
    case 'SELL':
      return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-red-500/20 text-red-400 border border-red-400/30">🔴 SELL</span>
    case 'WEAK_SELL':
      return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-yellow-500/20 text-yellow-400 border border-yellow-400/30">🟡 WSL</span>
    default:
      return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-semibold uppercase tracking-wider bg-gray-500/20 text-gray-400 border border-gray-400/30">⚪ HOLD</span>
  }
}

function getConfidenceColor(confidence: number) {
  if (confidence >= 0.7) return '#10b981' // emerald
  if (confidence >= 0.5) return '#f59e0b' // amber
  return '#ef4444' // red
}

function getVerdictColor(verdict: string): string {
  switch (verdict) {
    case 'BUY': return '#10b981'      // emerald
    case 'MODERATE': return '#f59e0b' // amber
    case 'SELL': return '#ef4444'     // red
    case 'WEAK_SELL': return '#eab308' // yellow
    default: return '#9ca3af'         // gray
  }
}
