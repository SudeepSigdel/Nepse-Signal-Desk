import type { SignalGroup, Verdict } from '../types'

export interface VerdictMeta {
  label: string
  group: SignalGroup
  text: string
  bg: string
  border: string
  dot: string
}

// Mirrors the backend's own verdict->color mapping (app/services/signal_service.py get_verdict):
// BUY=green, MODERATE=orange, SELL=red, WEAK_SELL=yellow, HOLD=gray, AVOID=red(muted).
const VERDICT_META: Record<string, VerdictMeta> = {
  BUY: {
    label: 'Buy',
    group: 'buy',
    text: 'text-emerald-700 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-500/10',
    border: 'border-emerald-200 dark:border-emerald-500/30',
    dot: 'bg-emerald-600 dark:bg-emerald-400',
  },
  MODERATE: {
    label: 'Moderate',
    group: 'watch',
    text: 'text-amber-700 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-500/10',
    border: 'border-amber-200 dark:border-amber-500/30',
    dot: 'bg-amber-600 dark:bg-amber-400',
  },
  HOLD: {
    label: 'Hold',
    group: 'hold',
    text: 'text-zinc-600 dark:text-zinc-400',
    bg: 'bg-zinc-100 dark:bg-zinc-800/60',
    border: 'border-zinc-200 dark:border-zinc-700',
    dot: 'bg-zinc-500 dark:bg-zinc-500',
  },
  AVOID: {
    label: 'Avoid',
    group: 'hold',
    text: 'text-zinc-600 dark:text-zinc-400',
    bg: 'bg-zinc-100 dark:bg-zinc-800/60',
    border: 'border-zinc-200 dark:border-zinc-700',
    dot: 'bg-zinc-500 dark:bg-zinc-500',
  },
  WEAK_SELL: {
    label: 'Weak sell',
    group: 'sell_risk',
    text: 'text-rose-600 dark:text-rose-400',
    bg: 'bg-rose-50 dark:bg-rose-500/10',
    border: 'border-rose-200 dark:border-rose-500/25',
    dot: 'bg-rose-500 dark:bg-rose-400',
  },
  SELL: {
    label: 'Sell risk',
    group: 'sell_risk',
    text: 'text-rose-800 dark:text-rose-300',
    bg: 'bg-rose-100 dark:bg-rose-500/20',
    border: 'border-rose-300 dark:border-rose-500/40',
    dot: 'bg-rose-700 dark:bg-rose-400',
  },
}

const FALLBACK_META: VerdictMeta = {
  label: 'Unrated',
  group: 'hold',
  text: 'text-zinc-500 dark:text-zinc-400',
  bg: 'bg-zinc-100 dark:bg-zinc-800/60',
  border: 'border-zinc-200 dark:border-zinc-700',
  dot: 'bg-zinc-400',
}

export function getVerdictMeta(verdict: string | null | undefined): VerdictMeta {
  if (!verdict) return FALLBACK_META
  return VERDICT_META[verdict] ?? FALLBACK_META
}

export function verdictGroup(verdict: string | null | undefined): SignalGroup {
  return getVerdictMeta(verdict).group
}

export const FILTER_TABS: Array<{ value: 'all' | SignalGroup | 'watchlist'; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'buy', label: 'Buy' },
  { value: 'watch', label: 'Watch' },
  { value: 'hold', label: 'Hold' },
  { value: 'sell_risk', label: 'Sell risk' },
  { value: 'watchlist', label: 'Watchlist' },
]

export type RsiZone = 'oversold' | 'overbought' | 'neutral'

export function rsiZone(rsi: number | null | undefined): RsiZone {
  if (rsi === null || rsi === undefined) return 'neutral'
  if (rsi < 30) return 'oversold'
  if (rsi > 70) return 'overbought'
  return 'neutral'
}

export type VolumeState = 'high' | 'low' | 'normal' | 'unknown'

export function volumeState(ratio: number | null | undefined): VolumeState {
  if (ratio === null || ratio === undefined) return 'unknown'
  if (ratio > 2) return 'high'
  if (ratio < 0.5) return 'low'
  return 'normal'
}

export const VOLUME_STATE_LABEL: Record<VolumeState, string> = {
  high: 'High volume',
  low: 'Low volume',
  normal: 'Normal',
  unknown: '—',
}

// Verdict as an implied direction, used to disambiguate confidence trend arrows.
export function verdictLabel(verdict: string | null | undefined): string {
  return getVerdictMeta(verdict).label
}

export const VERDICT_TYPES: Verdict[] = ['BUY', 'MODERATE', 'HOLD', 'WEAK_SELL', 'SELL', 'AVOID']

// Sober, plain-language summaries — deliberately avoids "AI says" / hype phrasing.
const VERDICT_SUMMARY: Record<string, string> = {
  BUY: 'Strong upward signal with high model confidence.',
  MODERATE: 'A building signal. Worth watching for confirmation before acting.',
  HOLD: 'No clear edge in either direction right now.',
  AVOID: 'No clear edge, and conditions lean unfavorable.',
  WEAK_SELL: 'Downside risk is elevated, though not at high confidence.',
  SELL: 'High-confidence downside risk.',
}

export function verdictSummary(verdict: string | null | undefined): string {
  if (!verdict) return 'Insufficient data for a signal.'
  return VERDICT_SUMMARY[verdict] ?? 'No clear edge in either direction right now.'
}
