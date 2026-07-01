import { useState, type FormEvent } from 'react'
import { useExitCheck } from '../../hooks/useExitCheck'
import { formatPercent, formatPrice } from '../../lib/format'

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'buy' | 'sell' }) {
  const toneClass =
    tone === 'buy'
      ? 'text-emerald-600 dark:text-emerald-400'
      : tone === 'sell'
        ? 'text-rose-600 dark:text-rose-400'
        : 'text-zinc-800 dark:text-zinc-200'
  return (
    <div>
      <p className="text-[11px] text-zinc-400 dark:text-zinc-500">{label}</p>
      <p className={`text-sm font-medium tabular-nums ${toneClass}`}>{value}</p>
    </div>
  )
}

export function PositionHelper({
  symbol,
  currentPrice,
  currentBuyConfidence,
}: {
  symbol: string
  currentPrice: number | null
  currentBuyConfidence: number | null
}) {
  const [entryDate, setEntryDate] = useState('')
  const [entryPrice, setEntryPrice] = useState('')
  const [quantity, setQuantity] = useState('')
  const { result, loading, error, check } = useExitCheck()

  const canSubmit = Boolean(entryDate) && Boolean(entryPrice) && currentPrice !== null && currentBuyConfidence !== null

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return
    await check({
      symbol,
      entry_date: entryDate,
      entry_price: parseFloat(entryPrice),
      current_price: currentPrice as number,
      current_buy_conf: currentBuyConfidence as number,
    })
  }

  const qty = quantity ? parseFloat(quantity) : null

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Position helper</p>
      <p className="mt-0.5 text-xs text-zinc-400 dark:text-zinc-500">Check exit guidance for a position you already hold.</p>

      <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Entry date
          <input
            type="date"
            value={entryDate}
            onChange={(e) => setEntryDate(e.target.value)}
            required
            className="rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Entry price
          <input
            type="number"
            step="0.01"
            value={entryPrice}
            onChange={(e) => setEntryPrice(e.target.value)}
            required
            className="rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Quantity (optional)
          <input
            type="number"
            step="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="w-full rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white disabled:opacity-40 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {loading ? 'Checking…' : 'Check position'}
          </button>
        </div>
      </form>

      {error && <p className="mt-3 text-xs text-rose-600 dark:text-rose-400">{error}</p>}

      {result && (
        <div
          className={`mt-4 rounded-md border p-3 ${
            result.should_exit
              ? 'border-rose-300 bg-rose-50 dark:border-rose-500/30 dark:bg-rose-500/10'
              : 'border-zinc-200 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800/60'
          }`}
        >
          <p className={`text-sm font-medium ${result.should_exit ? 'text-rose-700 dark:text-rose-300' : 'text-zinc-700 dark:text-zinc-300'}`}>
            {result.should_exit ? (result.reason ?? 'Exit criteria met') : 'No exit criteria triggered'}
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Days held" value={`${result.days_held} / ${result.days_held + result.days_remaining}`} />
            <Metric
              label="Current return"
              value={formatPercent(result.current_return_pct, { signed: true })}
              tone={result.current_return_pct >= 0 ? 'buy' : 'sell'}
            />
            <Metric label="Stop-loss distance" value={formatPercent(result.distance_to_stop_loss_pct)} />
            <Metric label="Position value" value={qty && currentPrice ? formatPrice(qty * currentPrice) : '—'} />
          </div>
          {result.risks.length > 0 && (
            <ul className="mt-3 space-y-1">
              {result.risks.map((risk) => (
                <li key={risk} className="flex gap-1.5 text-xs text-amber-700 dark:text-amber-400">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber-500" />
                  {risk}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
