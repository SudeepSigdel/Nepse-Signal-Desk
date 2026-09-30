import { CheckCircle2, Circle, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { dismissFirstSteps, hasVisitedAgents, isFirstStepsDismissed } from '../../lib/onboarding'
import type { PaperOrder } from '../../types'

/** Guided first steps for a new paper trader, ticked off from what actually happened. */
export function FirstStepsChecklist({ accountId, orders }: { accountId: number; orders: PaperOrder[] }) {
  const [dismissed, setDismissed] = useState(() => isFirstStepsDismissed(accountId))
  const steps = [
    { done: orders.length > 0, label: 'Place your first order', to: '/trade', cta: 'Trade' },
    {
      done: orders.some((o) => o.status === 'filled'),
      label: 'See it fill and check the fee breakdown',
      hint: 'Orders placed outside market hours fill at the next session’s close.',
    },
    { done: orders.some((o) => o.realized_pnl !== null), label: 'Close a trade and see your real profit after costs' },
    { done: hasVisitedAgents(), label: 'See how the trading bots decide', to: '/agents', cta: 'Bots' },
  ]
  const completed = steps.filter((s) => s.done).length
  if (dismissed || completed === steps.length) return null

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">First steps</h2>
          <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
            {completed} of {steps.length} done
          </p>
        </div>
        <button
          onClick={() => {
            dismissFirstSteps(accountId)
            setDismissed(true)
          }}
          aria-label="Hide first steps"
          className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-2 h-1 rounded-full bg-zinc-100 dark:bg-zinc-800">
        <div className="h-1 rounded-full bg-emerald-500" style={{ width: `${(completed / steps.length) * 100}%` }} />
      </div>
      <ul className="mt-3 space-y-2">
        {steps.map((step) => (
          <li key={step.label} className="flex items-start gap-2 text-sm">
            {step.done ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
            ) : (
              <Circle className="mt-0.5 h-4 w-4 shrink-0 text-zinc-300 dark:text-zinc-600" />
            )}
            <span className={step.done ? 'text-zinc-400 line-through dark:text-zinc-500' : 'text-zinc-700 dark:text-zinc-300'}>
              {step.label}
              {!step.done && step.hint && (
                <span className="block text-[11px] text-zinc-400 no-underline dark:text-zinc-500">{step.hint}</span>
              )}
            </span>
            {!step.done && step.to && (
              <Link to={step.to} className="ml-auto shrink-0 text-xs font-medium text-zinc-900 underline-offset-2 hover:underline dark:text-zinc-100">
                {step.cta} →
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
