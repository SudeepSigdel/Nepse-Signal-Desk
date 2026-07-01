export type MeterTone = 'buy' | 'sell' | 'neutral'

const FILL_CLASS: Record<MeterTone, string> = {
  buy: 'bg-emerald-600 dark:bg-emerald-500',
  sell: 'bg-rose-600 dark:bg-rose-500',
  neutral: 'bg-zinc-400 dark:bg-zinc-500',
}

export function ConfidenceMeter({
  value,
  label,
  tone = 'buy',
  className = '',
}: {
  value: number | null
  label?: string
  tone?: MeterTone
  className?: string
}) {
  const pct = value === null || value === undefined ? 0 : Math.max(0, Math.min(100, Math.round(value * 100)))

  return (
    <div className={className}>
      {label && (
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-zinc-500 dark:text-zinc-400">{label}</span>
          <span className="font-medium tabular-nums text-zinc-700 dark:text-zinc-300">
            {value === null || value === undefined ? '—' : `${pct}%`}
          </span>
        </div>
      )}
      <div className="h-1.5 w-full rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div
          className={`h-1.5 rounded-full transition-[width] ${FILL_CLASS[tone]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
