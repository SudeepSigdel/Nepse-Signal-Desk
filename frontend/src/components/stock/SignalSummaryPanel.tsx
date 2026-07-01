import { getSupportingFactors, getWarningFactors } from '../../lib/signalFactors'
import { verdictSummary } from '../../lib/verdict'
import type { SignalDetail } from '../../types'
import { ConfidenceMeter } from '../ui/ConfidenceMeter'

export function SignalSummaryPanel({ signal }: { signal: SignalDetail }) {
  const supporting = getSupportingFactors(signal)
  const warnings = getWarningFactors(signal)

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <ConfidenceMeter label="Buy confidence" value={signal.buy_confidence} tone="buy" />
        <ConfidenceMeter label="Sell confidence" value={signal.sell_confidence} tone="sell" />
      </div>

      <p className="mt-4 text-sm text-zinc-700 dark:text-zinc-300">{verdictSummary(signal.verdict)}</p>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
            Supporting factors
          </p>
          {supporting.length === 0 ? (
            <p className="text-xs text-zinc-400 dark:text-zinc-500">No specific bullish triggers active.</p>
          ) : (
            <ul className="space-y-1.5">
              {supporting.map((f) => (
                <li key={f.label} className="flex gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-emerald-500" />
                  <span>
                    {f.label}
                    {f.detail && <span className="text-zinc-400 dark:text-zinc-500"> — {f.detail}</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
            Warning factors
          </p>
          {warnings.length === 0 ? (
            <p className="text-xs text-zinc-400 dark:text-zinc-500">No elevated risk factors detected.</p>
          ) : (
            <ul className="space-y-1.5">
              {warnings.map((f) => (
                <li key={f.label} className="flex gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-rose-500" />
                  <span>
                    {f.label}
                    {f.detail && <span className="text-zinc-400 dark:text-zinc-500"> — {f.detail}</span>}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
