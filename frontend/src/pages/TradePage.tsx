import { ArrowLeftRight } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { FeeBreakdownCard } from '../components/paper/FeeBreakdownCard'
import { PaperDisclaimer } from '../components/paper/PaperDisclaimer'
import { PaperOnboarding } from '../components/paper/PaperOnboarding'
import { EmptyState } from '../components/ui/EmptyState'
import { SignalBadge } from '../components/ui/SignalBadge'
import { useStocksContext } from '../context/StocksContext'
import { useFeePreview } from '../hooks/useFeePreview'
import { usePaperAccounts } from '../hooks/usePaperAccounts'
import { usePolling } from '../hooks/usePolling'
import { apiErrorMessage, fetchQuote, fetchSignal, placePaperOrder } from '../lib/api'
import { formatConfidence, formatMoney, formatPrice } from '../lib/format'
import type { FeePreviewRequest, OrderSide, OrderType, PaperOrder, Quote } from '../types'

const inputClass =
  'rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100'
const cardClass = 'rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900'

function SourceBadge({ source }: { source: Quote['source'] }) {
  const live = source === 'live'
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
        live
          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
          : 'bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400'
      }`}
      title={live ? 'Last traded price during market hours' : 'Latest daily close from the data pipeline'}
    >
      {live ? 'Live' : 'End of day'}
    </span>
  )
}

function QuoteCard({ quote }: { quote: Quote }) {
  return (
    <div className={cardClass}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Link to={`/stocks/${quote.symbol}`} className="text-lg font-semibold text-zinc-900 hover:underline dark:text-zinc-50">
            {quote.symbol}
          </Link>
          <SourceBadge source={quote.source} />
        </div>
        <span className="text-xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{formatPrice(quote.price)}</span>
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
        <div>
          <dt className="text-zinc-400 dark:text-zinc-500">Prev close</dt>
          <dd className="tabular-nums text-zinc-700 dark:text-zinc-300">{formatPrice(quote.prev_close)}</dd>
        </div>
        <div>
          <dt className="text-zinc-400 dark:text-zinc-500">Day range</dt>
          <dd className="tabular-nums text-zinc-700 dark:text-zinc-300">
            {formatPrice(quote.day_low)} – {formatPrice(quote.day_high)}
          </dd>
        </div>
        <div className="col-span-2">
          <dt className="text-zinc-400 dark:text-zinc-500">±10% circuit band {quote.market_open ? 'today' : 'next session'}</dt>
          <dd className="tabular-nums text-zinc-700 dark:text-zinc-300">
            {formatPrice(quote.circuit_low)} – {formatPrice(quote.circuit_high)}
          </dd>
        </div>
      </dl>
      <p className="mt-2 text-[11px] text-zinc-400 dark:text-zinc-500">
        {quote.market_open && quote.source === 'live'
          ? 'Market is open: market orders fill immediately at the live price.'
          : quote.market_open
            ? 'Market is open, but live prices aren’t connected: orders queue and fill at today’s closing price.'
            : 'Market is closed: orders queue and fill at the next session’s closing price.'}{' '}
        As of {quote.as_of}.
      </p>
    </div>
  )
}

function ModelPanel({ symbol }: { symbol: string }) {
  const { data: signal, error } = usePolling(() => fetchSignal(symbol), [symbol])
  if (error || !signal) {
    return (
      <p className="text-xs text-zinc-400 dark:text-zinc-500">
        No model signal for {symbol} (it may be too new or too thinly traded for the model).
      </p>
    )
  }
  return (
    <div className="space-y-1.5 text-xs text-zinc-600 dark:text-zinc-400">
      <div className="flex items-center gap-2">
        <SignalBadge verdict={signal.verdict} />
        <span>Buy confidence {formatConfidence(signal.buy_confidence)}</span>
        {signal.sell_confidence !== null && <span>· Sell confidence {formatConfidence(signal.sell_confidence)}</span>}
      </div>
      <p>{signal.description}</p>
      <p className="text-[11px] text-zinc-400 dark:text-zinc-500">
        A second opinion to learn from, not an instruction. Compare it with your own reasoning.
      </p>
    </div>
  )
}

function OrderResult({ order }: { order: PaperOrder }) {
  const tone =
    order.status === 'filled'
      ? 'border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300'
      : order.status === 'pending'
        ? 'border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-300'
        : 'border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-500/30 dark:bg-rose-500/10 dark:text-rose-300'
  const verb = order.side === 'buy' ? 'Bought' : 'Sold'
  return (
    <div className={`rounded-md border p-3 text-xs ${tone}`}>
      {order.status === 'filled' && (
        <p>
          {verb} {order.qty} {order.symbol} at {formatPrice(order.fill_price)} ({order.price_source}). Net{' '}
          {formatMoney(order.fees?.net_amount)}.
        </p>
      )}
      {order.status === 'pending' && (
        <p>
          Order queued: {order.side} {order.qty} {order.symbol}. It fills at the next session close
          {order.order_type === 'limit' ? ` if the price reaches ${formatPrice(order.limit_price)}` : ''}.
          {order.reserved_cash > 0 && ` ${formatMoney(order.reserved_cash)} is reserved until then.`}
        </p>
      )}
      {order.status === 'rejected' && <p>Order rejected: {order.reject_reason}</p>}
    </div>
  )
}

export function TradePage() {
  const { stocks } = useStocksContext()
  const { accounts, account, loading, create, refresh, select } = usePaperAccounts()
  const [params, setParams] = useSearchParams()

  const [symbolInput, setSymbolInput] = useState((params.get('symbol') ?? '').toUpperCase())
  const symbol = (params.get('symbol') ?? '').toUpperCase()
  const [side, setSide] = useState<OrderSide>(params.get('side') === 'sell' ? 'sell' : 'buy')
  const [orderType, setOrderType] = useState<OrderType>('market')
  const [qty, setQty] = useState('10')
  const [limitPrice, setLimitPrice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [lastOrder, setLastOrder] = useState<PaperOrder | null>(null)
  const [error, setError] = useState<string | null>(null)

  const { data: quote, error: quoteError } = usePolling<Quote | null>(
    () => (symbol ? fetchQuote(symbol) : Promise.resolve(null)),
    [symbol],
    30_000
  )

  useEffect(() => setLastOrder(null), [symbol])

  const position = account?.positions.find((p) => p.symbol === symbol) ?? null
  const qtyNum = Number.parseInt(qty, 10)
  const limitNum = Number.parseFloat(limitPrice)
  const previewPrice = orderType === 'limit' && limitNum > 0 ? limitNum : quote?.price ?? 0

  const previewRequest: FeePreviewRequest | null = useMemo(() => {
    if (!quote || !(qtyNum > 0) || !(previewPrice > 0)) return null
    if (side === 'buy') return { side, price: previewPrice, qty: qtyNum }
    const heldDays = position ? Math.max(0, Math.floor((Date.now() - new Date(position.first_buy_date).getTime()) / 86_400_000)) : 0
    return { side, price: previewPrice, qty: qtyNum, avg_cost: position?.avg_cost ?? previewPrice, holding_days: heldDays }
  }, [quote, qtyNum, previewPrice, side, position])
  const fees = useFeePreview(previewRequest)

  const chooseSymbol = (e: FormEvent) => {
    e.preventDefault()
    const next = symbolInput.trim().toUpperCase()
    if (next) setParams({ symbol: next })
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!account || !symbol) return
    setSubmitting(true)
    setError(null)
    try {
      const order = await placePaperOrder(account.id, {
        symbol,
        side,
        order_type: orderType,
        qty: qtyNum,
        limit_price: orderType === 'limit' ? limitNum : null,
      })
      setLastOrder(order)
      refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (!loading && accounts.length === 0) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <PaperDisclaimer />
        <PaperOnboarding onCreate={() => create('My paper account')} />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Trade</h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">Place practice orders on real NEPSE prices.</p>
        </div>
        {account && (
          <div className="flex items-center gap-3 text-sm">
            {accounts.length > 1 && (
              <select value={account.id} onChange={(e) => select(Number(e.target.value))} className={inputClass}>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            )}
            <span className="text-zinc-500 dark:text-zinc-400">
              Available <span className="font-medium tabular-nums text-zinc-900 dark:text-zinc-100">{formatMoney(account.available_cash)}</span>
            </span>
            <Link to="/paper" className="font-medium text-zinc-900 underline-offset-2 hover:underline dark:text-zinc-100">
              Portfolio →
            </Link>
          </div>
        )}
      </div>

      <PaperDisclaimer />

      <form onSubmit={chooseSymbol} className="flex gap-2">
        <input
          list="trade-symbols"
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value)}
          placeholder="Symbol, e.g. NABIL"
          className={`${inputClass} flex-1 uppercase`}
        />
        <datalist id="trade-symbols">
          {stocks.map((s) => (
            <option key={s.symbol} value={s.symbol} />
          ))}
        </datalist>
        <button type="submit" className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900">
          Load
        </button>
      </form>

      {!symbol ? (
        <EmptyState icon={ArrowLeftRight} title="Pick a stock to trade" description="Any listed NEPSE equity works." />
      ) : quoteError ? (
        <p className="text-sm text-rose-600 dark:text-rose-400">No price data for {symbol}. Check the symbol.</p>
      ) : !quote ? (
        <p className="text-sm text-zinc-400">Loading quote…</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-5">
          <div className="space-y-4 md:col-span-3">
            <QuoteCard quote={quote} />
            <div className={cardClass}>
              <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">What the model says</h2>
              <ModelPanel symbol={symbol} />
            </div>
            {position && (
              <div className={`${cardClass} text-xs text-zinc-600 dark:text-zinc-400`}>
                You hold <span className="font-medium text-zinc-900 dark:text-zinc-100">{position.qty}</span> shares at an average
                cost of {formatPrice(position.avg_cost)} (fees included), since {position.first_buy_date}.
              </div>
            )}
          </div>

          <form onSubmit={submit} className={`${cardClass} space-y-3 md:col-span-2`}>
            <div className="grid grid-cols-2 gap-1 rounded-md bg-zinc-100 p-1 dark:bg-zinc-800">
              {(['buy', 'sell'] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setSide(s)}
                  className={`rounded px-2 py-1 text-sm font-medium capitalize ${
                    side === s
                      ? s === 'buy'
                        ? 'bg-emerald-600 text-white'
                        : 'bg-rose-600 text-white'
                      : 'text-zinc-500 dark:text-zinc-400'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              Order type
              <select value={orderType} onChange={(e) => setOrderType(e.target.value as OrderType)} className={inputClass}>
                <option value="market">Market</option>
                <option value="limit">Limit</option>
              </select>
            </label>

            <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
              Quantity {side === 'buy' ? '(min 10)' : position ? `(you hold ${position.qty})` : ''}
              <input type="number" min={1} step={1} value={qty} onChange={(e) => setQty(e.target.value)} className={inputClass} required />
            </label>

            {orderType === 'limit' && (
              <label className="flex flex-col gap-1 text-xs text-zinc-500 dark:text-zinc-400">
                Limit price
                <input
                  type="number"
                  step="0.1"
                  min={0}
                  value={limitPrice}
                  onChange={(e) => setLimitPrice(e.target.value)}
                  placeholder={quote.price.toFixed(1)}
                  className={inputClass}
                  required
                />
              </label>
            )}

            {fees && (
              <div className="rounded-md bg-zinc-50 p-2.5 dark:bg-zinc-800/60">
                <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                  Estimated costs at {formatPrice(previewPrice)}
                </p>
                <FeeBreakdownCard fees={fees} />
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !account}
              className={`w-full rounded-md px-3 py-2 text-sm font-semibold text-white disabled:opacity-50 ${
                side === 'buy' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'
              }`}
            >
              {submitting ? 'Placing…' : `${side === 'buy' ? 'Buy' : 'Sell'} ${symbol}`}
            </button>

            {error && <p className="text-xs text-rose-600 dark:text-rose-400">{error}</p>}
            {lastOrder && <OrderResult order={lastOrder} />}
          </form>
        </div>
      )}
    </div>
  )
}
