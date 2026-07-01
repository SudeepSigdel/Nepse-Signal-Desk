import { Line } from 'react-chartjs-2'
import { useConfidenceHistory } from '../../hooks/useConfidenceHistory'
import { useTheme } from '../../hooks/useTheme'
import '../../lib/chartRegistry'
import { baseChartOptions } from '../../lib/chartTheme'
import { formatDateShort } from '../../lib/format'
import { SignalBadge } from '../ui/SignalBadge'
import { trendFromDelta, TrendIndicator } from '../ui/TrendIndicator'

export function SignalHistoryPanel({
  symbol,
  confidence,
  verdict,
  date,
}: {
  symbol: string
  confidence: number | null
  verdict: string | null
  date: string | null
}) {
  const entries = useConfidenceHistory(symbol, confidence, verdict, date)
  const { isDark } = useTheme()

  if (entries.length < 2) {
    return (
      <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Signal history</p>
        <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">
          Confidence history builds up as this stock is viewed on different days. Check back tomorrow to see a trend.
        </p>
      </div>
    )
  }

  const delta = entries[entries.length - 1].confidence - entries[0].confidence
  const direction = trendFromDelta(delta, 0.02)

  const chartData = {
    labels: entries.map((e) => formatDateShort(e.date)),
    datasets: [
      {
        label: 'Confidence',
        data: entries.map((e) => Math.round(e.confidence * 100)),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        fill: true,
        borderWidth: 1.5,
        pointRadius: 2,
        tension: 0.2,
      },
    ],
  }

  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Signal history</p>
        <TrendIndicator direction={direction} />
      </div>
      <p className="mt-0.5 text-[11px] text-zinc-400 dark:text-zinc-500">
        Tracked from signals viewed in this browser, one entry per day.
      </p>
      <div className="mt-3 h-32">
        <Line data={chartData} options={baseChartOptions(isDark, { min: 0, max: 100 })} />
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {entries.slice(-14).map((e) => (
          <SignalBadge key={e.date} verdict={e.verdict} />
        ))}
      </div>
    </div>
  )
}
