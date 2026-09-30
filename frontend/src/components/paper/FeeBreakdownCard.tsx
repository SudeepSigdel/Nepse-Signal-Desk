import { formatMoney } from '../../lib/format'
import type { FeeBreakdown } from '../../types'

function Row({ label, value, hint, strong }: { label: string; value: number; hint?: string; strong?: boolean }) {
  return (
    <div className={`flex items-baseline justify-between gap-3 ${strong ? 'font-semibold text-zinc-900 dark:text-zinc-50' : ''}`}>
      <span>
        {label}
        {hint && <span className="ml-1 text-[11px] text-zinc-400 dark:text-zinc-500">{hint}</span>}
      </span>
      <span className="tabular-nums">{formatMoney(value)}</span>
    </div>
  )
}

/** Itemized NEPSE costs. Doubles as a lesson: most beginners underestimate round-trip costs. */
export function FeeBreakdownCard({ fees }: { fees: FeeBreakdown }) {
  const isSell = fees.side === 'sell'
  return (
    <div className="space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
      <Row label="Trade value" value={fees.trade_value} />
      <Row label="Broker commission" hint={`${(fees.commission_rate * 100).toFixed(2)}%`} value={fees.broker_commission} />
      <Row label="SEBON fee" hint="0.015%" value={fees.sebon_fee} />
      {isSell && <Row label="DP charge" hint="per sell" value={fees.dp_charge} />}
      {isSell && (
        <Row
          label="Capital gains tax"
          hint={fees.cgt_rate ? `${(fees.cgt_rate * 100).toFixed(1)}% of gain` : 'no gain, no tax'}
          value={fees.capital_gains_tax}
        />
      )}
      <div className="border-t border-zinc-200 pt-1 dark:border-zinc-700">
        <Row label={isSell ? 'You receive' : 'You pay'} value={fees.net_amount} strong />
      </div>
    </div>
  )
}
