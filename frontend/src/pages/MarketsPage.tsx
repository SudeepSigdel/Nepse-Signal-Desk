import { useState } from 'react'
import { MoversView } from '../components/markets/MoversView'
import { SectorsView } from '../components/markets/SectorsView'

type Tab = 'movers' | 'sectors'

const TABS: Array<{ value: Tab; label: string }> = [
  { value: 'movers', label: 'Movers' },
  { value: 'sectors', label: 'Sectors' },
]

export function MarketsPage() {
  const [tab, setTab] = useState<Tab>('movers')

  return (
    <div className="mx-auto max-w-[1400px] space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Markets</h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
            Where today's price, activity, and sentiment are concentrated across the model-ready universe.
          </p>
        </div>
        <div className="flex gap-0.5 rounded-md border border-zinc-200 bg-zinc-50 p-0.5 dark:border-zinc-800 dark:bg-zinc-900">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
                tab === t.value
                  ? 'bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-50'
                  : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === 'movers' ? <MoversView /> : <SectorsView />}
    </div>
  )
}
