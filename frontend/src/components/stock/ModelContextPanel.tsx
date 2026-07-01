import type { SignalDetail } from '../../types'

export function ModelContextPanel({ signal }: { signal: SignalDetail }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">What the model is seeing</p>
      <p className="mt-2 text-xs leading-relaxed text-zinc-500 dark:text-zinc-400">
        The model estimates the probability that {signal.symbol} moves more than 1% over the next 10 trading days,
        based on recent price action, momentum (RSI, MACD), volatility (Bollinger bands), and volume. It does not use
        news, fundamentals, or macroeconomic data. A higher confidence score means this pattern has historically been
        followed by the predicted move more often — it is not a guarantee.
      </p>
    </div>
  )
}
