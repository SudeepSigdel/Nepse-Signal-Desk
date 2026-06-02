/**
 * Reusable Signal Card Component
 * Shows 5-level verdict (BUY/MODERATE/SELL/WEAK_SELL/HOLD) with dual confidence scores
 */

interface SignalCardProps {
  verdict_color: string
  buy_confidence: number
  sell_confidence?: number | null
  description: string
  active_signals: string[]
  close?: number
}

export function SignalCard({ 
  verdict_color, 
  buy_confidence,
  sell_confidence,
  description, 
  active_signals,
  close 
}: SignalCardProps) {
  const getSignalVisuals = () => {
    switch (verdict_color) {
      case 'green':
        return {
          accent: 'from-emerald-400/20 via-emerald-400/10 to-transparent',
          actionText: 'Strong buy setup',
          bgClass: 'bg-emerald-50/[0.8] dark:bg-emerald-500/[0.08] border-emerald-200 dark:border-emerald-500/25',
          textClass: 'text-emerald-700 dark:text-emerald-300',
          riskText: 'Lower relative risk',
          confidenceLabel: 'Buy confidence'
        }
      case 'amber':
      case 'orange':
        return {
          accent: 'from-amber-300/20 via-amber-300/10 to-transparent',
          actionText: 'Watch for a cleaner entry',
          bgClass: 'bg-amber-50/[0.8] dark:bg-amber-500/[0.08] border-amber-200 dark:border-amber-500/25',
          textClass: 'text-amber-700 dark:text-amber-300',
          riskText: 'Moderate risk',
          confidenceLabel: 'Buy confidence'
        }
      case 'gray':
        return {
          accent: 'from-slate-300/20 via-slate-300/10 to-transparent',
          actionText: 'No clear edge',
          bgClass: 'bg-slate-100/[0.8] dark:bg-slate-500/[0.08] border-slate-200 dark:border-slate-500/20',
          textClass: 'text-slate-700 dark:text-slate-300',
          riskText: 'Mixed signals',
          confidenceLabel: 'Confidence'
        }
      case 'yellow':
        return {
          accent: 'from-yellow-300/20 via-yellow-300/10 to-transparent',
          actionText: 'Weak sell pressure',
          bgClass: 'bg-yellow-50/[0.8] dark:bg-yellow-500/[0.08] border-yellow-200 dark:border-yellow-500/25',
          textClass: 'text-yellow-700 dark:text-yellow-300',
          riskText: 'Upside is fading',
          confidenceLabel: 'Sell confidence'
        }
      case 'red':
        return {
          accent: 'from-rose-300/20 via-rose-300/10 to-transparent',
          actionText: 'High sell risk',
          bgClass: 'bg-rose-50/[0.8] dark:bg-red-500/[0.08] border-rose-200 dark:border-red-500/25',
          textClass: 'text-rose-700 dark:text-rose-300',
          riskText: 'Downside risk is elevated',
          confidenceLabel: 'Sell confidence'
        }
      default:
        return {
          accent: 'from-white/10 via-white/5 to-transparent',
          actionText: 'Signal unavailable',
          bgClass: 'bg-slate-50 dark:bg-white/5 border-slate-200 dark:border-white/10',
          textClass: 'text-slate-600 dark:text-slate-300',
          riskText: 'No clean classification',
          confidenceLabel: 'Confidence'
        }
    }
  }

  const visuals = getSignalVisuals()

  const getActionSteps = () => {
    switch (verdict_color) {
      case 'green':
        return [
          'Check recent company news',
          'Set a stop-loss below support',
          'Scale in instead of going all-in'
        ]
      case 'amber':
      case 'orange':
        return [
          'Wait for a better entry',
          'Watch volume and trend confirmation',
          'Avoid chasing the current price'
        ]
      case 'gray':
        return [
          'Look for a cleaner setup',
          'Use alerts instead of guessing',
          'Let the market prove direction'
        ]
      case 'yellow':
        return [
          'Treat the move cautiously',
          'Review whether the trend is breaking',
          'Protect profits if you are already in'
        ]
      case 'red':
        return [
          'Avoid new entries',
          'Consider reducing exposure',
          'Wait for the trend to reset'
        ]
      default:
        return []
    }
  }

  // Get color for confidence bar based on confidence level
  const getConfidenceBarColor = (isSell: boolean) => {
    if (isSell) {
      return verdict_color === 'red' ? 'bg-red-500' :
             verdict_color === 'yellow' ? 'bg-yellow-500' :
             'bg-neutral-500'
    } else {
      return verdict_color === 'green' ? 'bg-green-500' :
             verdict_color === 'amber' || verdict_color === 'orange' ? 'bg-amber-500' :
             'bg-neutral-500'
    }
  }

  const primaryConfidence = verdict_color === 'red' || verdict_color === 'yellow' 
    ? sell_confidence 
    : buy_confidence
  const confidenceIsSell = verdict_color === 'red' || verdict_color === 'yellow'

  return (
    <div className={`glass-panel rounded-2xl border ${visuals.bgClass}`}>
      <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${visuals.accent}`} />
      <div className="relative p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <div className={`mb-4 inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] ${visuals.textClass}`}>
              {verdict_color.toUpperCase().replace('_', ' ')}
            </div>
            <h3 className={`font-display text-2xl font-bold tracking-tight sm:text-3xl ${visuals.textClass}`}>
              {visuals.actionText}
            </h3>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-700 dark:text-slate-300/85">
              {visuals.riskText}
            </p>
          </div>

          {close !== undefined && close !== null && (
            <div className="rounded-2xl border border-black/5 dark:border-white/8 bg-black/5 dark:bg-white/4 px-4 py-3 text-right shadow-[0_12px_40px_rgba(0,0,0,0.06)] dark:shadow-[0_12px_40px_rgba(0,0,0,0.16)]">
              <p className="text-[0.7rem] uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">Current price</p>
              <p className="mt-1 font-display text-3xl font-semibold text-slate-950 dark:text-white">Rs. {close.toFixed(2)}</p>
            </div>
          )}
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-black/5 dark:border-white/8 bg-black/5 dark:bg-black/18 p-4">
            <div className="mb-2 flex items-center justify-between gap-4">
              <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{visuals.confidenceLabel}</span>
              <span className={`font-display text-2xl font-bold ${visuals.textClass}`}>
                {(primaryConfidence! * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/8">
              <div
                className={`h-full rounded-full transition-all ${getConfidenceBarColor(confidenceIsSell)}`}
                style={{ width: `${primaryConfidence! * 100}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {primaryConfidence! >= 0.75 ? 'Very high conviction' :
               primaryConfidence! >= 0.65 ? 'High conviction' :
               primaryConfidence! >= 0.55 ? 'Moderate conviction' :
               primaryConfidence! >= 0.45 ? 'Low conviction' :
               'Very low conviction'}
            </p>
          </div>

          {sell_confidence !== null && sell_confidence !== undefined && !confidenceIsSell && (
            <div className="rounded-2xl border border-black/5 dark:border-white/8 bg-black/5 dark:bg-black/18 p-4">
              <div className="mb-2 flex items-center justify-between gap-4">
                <span className="text-sm font-medium text-slate-600 dark:text-slate-300">Sell confidence</span>
                <span className="font-display text-2xl font-bold text-rose-600 dark:text-rose-300">
                  {(sell_confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/8">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-rose-500 to-rose-400 dark:from-rose-400 dark:to-rose-300 transition-all"
                  style={{ width: `${sell_confidence * 100}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                {sell_confidence >= 0.65 ? 'Downside risk is elevated' :
                 sell_confidence >= 0.55 ? 'Downside risk is building' :
                 'Downside risk is limited'}
              </p>
            </div>
          )}
        </div>

        <div className="mt-5 rounded-2xl border border-black/5 dark:border-white/8 bg-black/[0.02] dark:bg-white/[0.03] p-4">
          <p className="text-sm leading-6 text-slate-700 dark:text-slate-200/90">{description}</p>
        </div>

        {active_signals.length > 0 && (
          <div className="mt-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">Why this signal</p>
            <div className="flex flex-wrap gap-2">
              {active_signals.map((signal) => (
                <span
                  key={signal}
                  className="inline-flex items-center gap-2 rounded-full border border-blue-200 dark:border-[#7aa2f7]/25 bg-blue-50 dark:bg-[#7aa2f7]/10 px-3 py-1 text-xs font-medium text-blue-700 dark:text-[#bfd4ff]"
                >
                  <span className="h-1.5 w-1.5 rounded-full bg-blue-600 dark:bg-[#8dd3ff]" />
                  {signal}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="mt-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">What to do next</p>
          <div className="grid gap-2">
            {getActionSteps().map((step, idx) => (
              <div key={idx} className="flex gap-3 rounded-xl border border-black/5 dark:border-white/6 bg-black/[0.02] dark:bg-black/12 px-3 py-2">
                <div className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                  verdict_color === 'green' ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' :
                  verdict_color === 'amber' || verdict_color === 'orange' ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300' :
                  verdict_color === 'gray' ? 'bg-slate-500/15 text-slate-600 dark:text-slate-300' :
                  verdict_color === 'yellow' ? 'bg-yellow-500/15 text-yellow-700 dark:text-yellow-300' :
                  'bg-rose-500/15 text-rose-700 dark:text-rose-300'
                }`}>
                  {idx + 1}
                </div>
                <p className="pt-1 text-sm text-slate-600 dark:text-slate-300">{step}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
