import { Minus, TrendingDown, TrendingUp } from 'lucide-react'

export type TrendDirection = 'up' | 'down' | 'flat'

export function trendFromDelta(delta: number | null | undefined, threshold = 0.01): TrendDirection {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return 'flat'
  if (delta > threshold) return 'up'
  if (delta < -threshold) return 'down'
  return 'flat'
}

const LABEL: Record<TrendDirection, string> = {
  up: 'Improving',
  down: 'Weakening',
  flat: 'Stable',
}

const CLASS: Record<TrendDirection, string> = {
  up: 'text-emerald-600 dark:text-emerald-400',
  down: 'text-rose-600 dark:text-rose-400',
  flat: 'text-zinc-400 dark:text-zinc-500',
}

const ICON = { up: TrendingUp, down: TrendingDown, flat: Minus }

export function TrendIndicator({
  direction,
  showLabel = true,
  className = '',
}: {
  direction: TrendDirection
  showLabel?: boolean
  className?: string
}) {
  const Icon = ICON[direction]
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap text-xs font-medium ${CLASS[direction]} ${className}`}>
      <Icon className="h-3.5 w-3.5" />
      {showLabel && LABEL[direction]}
    </span>
  )
}
