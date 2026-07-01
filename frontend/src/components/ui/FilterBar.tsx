import { FILTER_TABS } from '../../lib/verdict'
import type { SignalGroup } from '../../types'

export type FilterValue = 'all' | SignalGroup | 'watchlist'

export function FilterBar({
  value,
  onChange,
  counts,
}: {
  value: FilterValue
  onChange: (value: FilterValue) => void
  counts?: Partial<Record<FilterValue, number>>
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {FILTER_TABS.map((tab) => {
        const active = value === tab.value
        const count = counts?.[tab.value]
        return (
          <button
            key={tab.value}
            onClick={() => onChange(tab.value)}
            className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
              active
                ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900'
                : 'border-zinc-200 bg-white text-zinc-600 hover:border-zinc-300 hover:text-zinc-900 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:border-zinc-700 dark:hover:text-zinc-100'
            }`}
          >
            {tab.label}
            {count !== undefined && <span className="ml-1 opacity-70">{count}</span>}
          </button>
        )
      })}
    </div>
  )
}
