import { Clock, Coins, Scale } from 'lucide-react'
import { useState } from 'react'
import { apiErrorMessage } from '../../lib/api'

const STEPS = [
  {
    icon: Coins,
    title: 'Rs 10,00,000 of virtual money',
    body: 'Trade any listed NEPSE stock at real prices. Nothing you do here touches real money.',
  },
  {
    icon: Scale,
    title: 'Real costs, real rules',
    body: 'Every trade pays broker commission, the SEBON fee, the DP charge and capital gains tax. Orders follow the ±10% circuit band, the 10-share minimum and no short selling.',
  },
  {
    icon: Clock,
    title: 'When orders fill',
    body: 'During market hours (Mon–Fri, 11:00–15:00) market orders fill at the live price when it is available. Otherwise they wait and fill at the next session’s closing price.',
  },
]

/** First-run explainer shown instead of an empty state when the user has no paper account yet. */
export function PaperOnboarding({ onCreate }: { onCreate: () => Promise<unknown> }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const start = async () => {
    setBusy(true)
    setError(null)
    try {
      await onCreate()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Learn to trade NEPSE without risking a rupee</h2>
      <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">Here is how paper trading works in three steps.</p>
      <ol className="mt-4 grid gap-3 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step.title} className="rounded-md bg-zinc-50 p-3 dark:bg-zinc-800/60">
            <div className="flex items-center gap-2 text-sm font-medium text-zinc-900 dark:text-zinc-100">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-zinc-900 text-xs text-white dark:bg-zinc-100 dark:text-zinc-900">
                {i + 1}
              </span>
              <step.icon className="h-4 w-4 text-zinc-400" />
              {step.title}
            </div>
            <p className="mt-1.5 text-xs leading-relaxed text-zinc-600 dark:text-zinc-400">{step.body}</p>
          </li>
        ))}
      </ol>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          onClick={start}
          disabled={busy}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? 'Opening…' : 'Open my paper account'}
        </button>
        <span className="text-xs text-zinc-400 dark:text-zinc-500">You can reset it any time.</span>
        {error && <span className="text-xs text-rose-600 dark:text-rose-400">{error}</span>}
      </div>
    </div>
  )
}
