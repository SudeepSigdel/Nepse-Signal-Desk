import { Trophy, Wallet } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { EquityChart } from '../components/paper/EquityChart'
import { FeeBreakdownCard } from '../components/paper/FeeBreakdownCard'
import { PaperDisclaimer } from '../components/paper/PaperDisclaimer'
import { EmptyState } from '../components/ui/EmptyState'
import { usePaperAccounts } from '../hooks/usePaperAccounts'
import { usePaperOrders } from '../hooks/usePaperOrders'
import { usePolling } from '../hooks/usePolling'
import { apiErrorMessage, cancelPaperOrder, fetchLeaderboard, fetchPaperEquity, resetPaperAccount } from '../lib/api'
import { formatDate, formatMoney, formatPercent, formatPrice } from '../lib/format'
import type { PaperOrder } from '../types'

const cardClass = 'rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900'
const thClass = 'px-2 py-1.5 text-left text-[11px] font-medium text-zinc-400 dark:text-zinc-500'
const tdClass = 'px-2 py-1.5 tabular-nums text-zinc-700 dark:text-zinc-300'

function pnlTone(value: number | null | undefined) {
  if (value === null || value === undefined || value === 0) return 'text-zinc-800 dark:text-zinc-200'
  return value > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <p className="text-[11px] text-zinc-400 dark:text-zinc-500">{label}</p>
      <p className={`text-base font-semibold tabular-nums ${tone ?? 'text-zinc-900 dark:text-zinc-50'}`}>{value}</p>
    </div>
  )
}

const STATUS_STYLES: Record<PaperOrder['status'], string> = {
  filled: 'text-emerald-600 dark:text-emerald-400',
  pending: 'text-sky-600 dark:text-sky-400',
  rejected: 'text-rose-600 dark:text-rose-400',
  cancelled: 'text-zinc-400 dark:text-zinc-500',
  expired: 'text-zinc-400 dark:text-zinc-500',
}

function OrderRow({ order, onCancel }: { order: PaperOrder; onCancel: (id: number) => void }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <tr className="border-t border-zinc-100 dark:border-zinc-800">
        <td className={tdClass}>{formatDate(order.created_at)}</td>
        <td className={`${tdClass} font-medium`}>
          <Link to={`/trade?symbol=${order.symbol}`} className="hover:underline">
            {order.symbol}
          </Link>
        </td>
        <td className={`${tdClass} capitalize`}>
          {order.side} · {order.order_type}
          {order.limit_price ? ` @ ${formatPrice(order.limit_price)}` : ''}
        </td>
        <td className={tdClass}>{order.qty}</td>
        <td className={tdClass}>{order.fill_price ? `${formatPrice(order.fill_price)} (${order.price_source})` : '—'}</td>
        <td className={`${tdClass} ${pnlTone(order.realized_pnl)}`}>
          {order.realized_pnl !== null ? formatMoney(order.realized_pnl, { signed: true }) : '—'}
        </td>
        <td className={`${tdClass} capitalize ${STATUS_STYLES[order.status]}`} title={order.reject_reason ?? undefined}>
          {order.status}
        </td>
        <td className={`${tdClass} text-right`}>
          {order.status === 'pending' && (
            <button onClick={() => onCancel(order.id)} className="text-xs font-medium text-zinc-400 hover:text-rose-600">
              Cancel
            </button>
          )}
          {order.fees && (
            <button onClick={() => setOpen((v) => !v)} className="text-xs font-medium text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200">
              {open ? 'Hide fees' : 'Fees'}
            </button>
          )}
        </td>
      </tr>
      {(open && order.fees) || order.reject_reason || order.note ? (
        <tr>
          <td colSpan={8} className="px-2 pb-2">
            {order.reject_reason && <p className="text-xs text-zinc-500 dark:text-zinc-400">{order.reject_reason}</p>}
            {order.note && <p className="text-xs text-zinc-500 dark:text-zinc-400">{order.note}</p>}
            {open && order.fees && (
              <div className="max-w-xs rounded-md bg-zinc-50 p-2.5 dark:bg-zinc-800/60">
                <FeeBreakdownCard fees={order.fees} />
              </div>
            )}
          </td>
        </tr>
      ) : null}
    </>
  )
}

export function PaperPortfolioPage() {
  const { accounts, account, loading, create, refresh, select } = usePaperAccounts()
  const { orders, refresh: refreshOrders } = usePaperOrders(account?.id ?? null)
  const { data: equity } = usePolling(() => (account ? fetchPaperEquity(account.id) : Promise.resolve([])), [account?.id])
  const { data: board } = usePolling(fetchLeaderboard, [])
  const [error, setError] = useState<string | null>(null)

  const cancel = async (orderId: number) => {
    try {
      await cancelPaperOrder(orderId)
      refreshOrders()
      refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    }
  }

  const reset = async () => {
    if (!account || !window.confirm(`Reset "${account.name}"? All positions and history will be cleared.`)) return
    await resetPaperAccount(account.id)
    refresh()
    refreshOrders()
  }

  if (!loading && accounts.length === 0) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-4 sm:p-6">
        <PaperDisclaimer />
        <EmptyState
          icon={Wallet}
          title="No paper account yet"
          description="Open one with Rs 10,00,000 of virtual money to start practising."
          action={
            <button
              onClick={() => create('My paper account')}
              className="mt-2 rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              Open account
            </button>
          }
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Paper trading</h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">Your virtual portfolio, orders and how you rank.</p>
        </div>
        <div className="flex items-center gap-2">
          {accounts.length > 1 && account && (
            <select
              value={account.id}
              onChange={(e) => select(Number(e.target.value))}
              className="rounded-md border border-zinc-200 bg-white px-2 py-1.5 text-sm dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
            >
              {accounts.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          )}
          <Link to="/trade" className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900">
            New order
          </Link>
        </div>
      </div>

      <PaperDisclaimer />
      {error && <p className="text-xs text-rose-600 dark:text-rose-400">{error}</p>}

      {account && (
        <>
          <div className={`${cardClass} grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6`}>
            <Stat label="Equity" value={formatMoney(account.equity)} />
            <Stat label="Return" value={formatPercent(account.return_pct, { signed: true, digits: 2 })} tone={pnlTone(account.return_pct)} />
            <Stat label="Available cash" value={formatMoney(account.available_cash)} />
            <Stat label="Unrealized P&L" value={formatMoney(account.unrealized_pnl, { signed: true })} tone={pnlTone(account.unrealized_pnl)} />
            <Stat label="Realized P&L" value={formatMoney(account.realized_pnl, { signed: true })} tone={pnlTone(account.realized_pnl)} />
            <Stat label="Fees & tax paid" value={formatMoney(account.fees_paid)} />
          </div>

          <div className={cardClass}>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Equity curve</h2>
              <span className="text-[11px] text-zinc-400 dark:text-zinc-500">Dashed line: starting cash {formatMoney(account.starting_cash)}</span>
            </div>
            <EquityChart points={equity ?? []} startingCash={account.starting_cash} />
          </div>

          <div className={cardClass}>
            <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Positions</h2>
            {account.positions.length === 0 ? (
              <p className="text-xs text-zinc-400 dark:text-zinc-500">
                No open positions. <Link to="/trade" className="underline">Place your first order</Link>.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      {['Symbol', 'Qty', 'Avg cost', 'Last', 'Value', 'Unrealized', ''].map((h) => (
                        <th key={h} className={thClass}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {account.positions.map((p) => (
                      <tr key={p.symbol} className="border-t border-zinc-100 dark:border-zinc-800">
                        <td className={`${tdClass} font-medium`}>
                          <Link to={`/stocks/${p.symbol}`} className="hover:underline">
                            {p.symbol}
                          </Link>
                        </td>
                        <td className={tdClass}>{p.qty}</td>
                        <td className={tdClass}>{formatPrice(p.avg_cost)}</td>
                        <td className={tdClass}>
                          {formatPrice(p.last_price)}
                          {p.price_source === 'live' && <span className="ml-1 text-[10px] text-emerald-500">live</span>}
                        </td>
                        <td className={tdClass}>{formatMoney(p.market_value)}</td>
                        <td className={`${tdClass} ${pnlTone(p.unrealized_pnl)}`}>
                          {formatMoney(p.unrealized_pnl, { signed: true })} ({formatPercent(p.unrealized_pct, { signed: true })})
                        </td>
                        <td className={`${tdClass} text-right`}>
                          <Link to={`/trade?symbol=${p.symbol}&side=sell`} className="text-xs font-medium text-rose-600 hover:underline">
                            Sell
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className={cardClass}>
            <h2 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-100">Orders</h2>
            {orders.length === 0 ? (
              <p className="text-xs text-zinc-400 dark:text-zinc-500">No orders yet.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr>
                      {['Placed', 'Symbol', 'Order', 'Qty', 'Fill', 'Realized', 'Status', ''].map((h) => (
                        <th key={h} className={thClass}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((o) => (
                      <OrderRow key={o.id} order={o} onCancel={cancel} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="flex justify-end">
            <button onClick={reset} className="text-xs font-medium text-zinc-400 hover:text-rose-600 dark:text-zinc-500">
              Reset this account
            </button>
          </div>
        </>
      )}

      <div className={cardClass}>
        <h2 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          <Trophy className="h-4 w-4 text-amber-500" /> Leaderboard
        </h2>
        {!board || board.length === 0 ? (
          <p className="text-xs text-zinc-400 dark:text-zinc-500">No traders yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                {['#', 'Trader', 'Account', 'Trades', 'Return'].map((h) => (
                  <th key={h} className={thClass}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {board.map((row) => (
                <tr
                  key={row.account_id}
                  className={`border-t border-zinc-100 dark:border-zinc-800 ${row.account_id === account?.id ? 'bg-zinc-50 dark:bg-zinc-800/50' : ''}`}
                >
                  <td className={tdClass}>{row.rank}</td>
                  <td className={tdClass}>
                    {row.trader}
                    {row.is_agent && <span className="ml-1 rounded bg-violet-100 px-1 text-[10px] text-violet-700 dark:bg-violet-500/15 dark:text-violet-300">bot</span>}
                  </td>
                  <td className={tdClass}>{row.account_name}</td>
                  <td className={tdClass}>{row.trades}</td>
                  <td className={`${tdClass} ${pnlTone(row.return_pct)}`}>{formatPercent(row.return_pct, { signed: true, digits: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
