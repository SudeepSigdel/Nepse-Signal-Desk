import { Briefcase } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'
import { useStocksContext } from '../context/StocksContext'
import { useHoldingsExitStatus } from '../hooks/useHoldingsExitStatus'
import { usePositions } from '../hooks/usePositions'
import { formatDate, formatPercent, formatPrice } from '../lib/format'

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'buy' | 'sell' }) {
  const toneClass =
    tone === 'buy' ? 'text-emerald-600 dark:text-emerald-400' : tone === 'sell' ? 'text-rose-600 dark:text-rose-400' : 'text-zinc-800 dark:text-zinc-200'
  return (
    <div>
      <p className="text-[11px] text-zinc-400 dark:text-zinc-500">{label}</p>
      <p className={`text-sm font-medium tabular-nums ${toneClass}`}>{value}</p>
    </div>
  )
}

export function PortfolioPage() {
  const { stocks } = useStocksContext()
  const { holdings, addHolding, removeHolding } = usePositions()
  const statusMap = useHoldingsExitStatus(holdings, stocks)

  const [symbol, setSymbol] = useState('')
  const [entryDate, setEntryDate] = useState('')
  const [entryPrice, setEntryPrice] = useState('')
  const [quantity, setQuantity] = useState('')

  const handleAdd = (e: FormEvent) => {
    e.preventDefault()
    if (!symbol || !entryDate || !entryPrice) return
    addHolding({
      symbol: symbol.toUpperCase(),
      entryDate,
      entryPrice: parseFloat(entryPrice),
      quantity: quantity ? parseFloat(quantity) : null,
    })
    setSymbol('')
    setEntryDate('')
    setEntryPrice('')
    setQuantity('')
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <div>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Portfolio</h1>
        <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
          Track positions you hold and get exit discipline guidance based on model signals.
        </p>
      </div>

      <form
        onSubmit={handleAdd}
        className="grid grid-cols-2 gap-3 rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900 sm:grid-cols-5"
      >
        <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
          Symbol
          <input
            list="portfolio-symbols"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="e.g. NHPC"
            required
            className="rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm uppercase text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
          />
          <datalist id="portfolio-symbols">
            {stocks.map((s) => (
              <option key={s.symbol} value={s.symbol} />
            ))}
          </datalist>
        </label>
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
            className="w-full rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
          >
            Add holding
          </button>
        </div>
      </form>

      {holdings.length === 0 ? (
        <EmptyState
          icon={Briefcase}
          title="No holdings tracked yet"
          description="Add a position above to get exit guidance based on time, stop-loss, and signal decay."
        />
      ) : (
        <div className="space-y-3">
          {holdings.map((holding) => {
            const stock = stocks.find((s) => s.symbol === holding.symbol)
            const status = statusMap[holding.id]
            const currentPrice = stock?.close ?? null
            const returnPct =
              status?.current_return_pct ?? (currentPrice !== null ? ((currentPrice - holding.entryPrice) / holding.entryPrice) * 100 : null)

            return (
              <div key={holding.id} className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <Link to={`/stocks/${holding.symbol}`} className="text-sm font-semibold text-zinc-900 hover:underline dark:text-zinc-100">
                      {holding.symbol}
                    </Link>
                    <p className="text-xs text-zinc-400 dark:text-zinc-500">
                      Entered {formatDate(holding.entryDate)} at {formatPrice(holding.entryPrice)}
                      {holding.quantity ? ` · ${holding.quantity} shares` : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => removeHolding(holding.id)}
                    className="text-xs font-medium text-zinc-400 hover:text-rose-600 dark:text-zinc-500 dark:hover:text-rose-400"
                  >
                    Remove
                  </button>
                </div>

                {!stock ? (
                  <p className="mt-3 text-xs text-zinc-400 dark:text-zinc-500">
                    Not in the current model-ready universe — exit guidance unavailable.
                  </p>
                ) : (
                  <>
                    <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-5">
                      <Metric label="Current price" value={formatPrice(currentPrice)} />
                      <Metric
                        label="Return"
                        value={returnPct === null ? '—' : formatPercent(returnPct, { signed: true })}
                        tone={returnPct !== null && returnPct >= 0 ? 'buy' : 'sell'}
                      />
                      <Metric label="Days held" value={status ? `${status.days_held} / ${status.days_held + status.days_remaining}` : '—'} />
                      <Metric label="Stop-loss distance" value={status ? formatPercent(status.distance_to_stop_loss_pct) : '—'} />
                      <Metric
                        label="Position value"
                        value={holding.quantity && currentPrice ? formatPrice(holding.quantity * currentPrice) : '—'}
                      />
                    </div>

                    {status && (
                      <div
                        className={`mt-3 rounded-md border p-2.5 text-xs ${
                          status.should_exit
                            ? 'border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300'
                            : status.risks.length > 0
                              ? 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300'
                              : 'border-zinc-200 bg-zinc-50 text-zinc-600 dark:border-zinc-700 dark:bg-zinc-800/60 dark:text-zinc-400'
                        }`}
                      >
                        <p className="font-medium">
                          {status.should_exit ? status.reason ?? 'Exit criteria met' : status.risks.length > 0 ? 'Signal weakening' : 'Position looks stable'}
                        </p>
                        {status.risks.length > 0 && (
                          <ul className="mt-1 space-y-0.5">
                            {status.risks.map((risk) => (
                              <li key={risk}>{risk}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
