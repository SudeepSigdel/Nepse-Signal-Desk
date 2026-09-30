import { AreaSeries, LineSeries, LineStyle, createChart } from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { useTheme } from '../../hooks/useTheme'
import { CHART_COLORS } from '../../lib/chartTheme'
import type { PaperEquityPoint } from '../../types'

/** Daily account equity (from settlement snapshots) against the starting-cash baseline. */
export function EquityChart({ points, startingCash }: { points: PaperEquityPoint[]; startingCash: number }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { isDark } = useTheme()

  useEffect(() => {
    const container = containerRef.current
    if (!container || points.length === 0) return

    const textColor = isDark ? CHART_COLORS.textDark : CHART_COLORS.textLight
    const gridColor = isDark ? CHART_COLORS.gridDark : CHART_COLORS.gridLight
    const chart = createChart(container, {
      autoSize: true,
      layout: { background: { color: 'transparent' }, textColor },
      grid: { vertLines: { visible: false }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor },
      handleScroll: false,
      handleScale: false,
    })

    const last = points[points.length - 1].equity
    const up = last >= startingCash
    const lineColor = up ? '#10b981' : '#f43f5e'
    const equity = chart.addSeries(AreaSeries, {
      lineColor,
      topColor: up ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)',
      bottomColor: 'rgba(0, 0, 0, 0)',
      lineWidth: 2,
    })
    equity.setData(points.map((p) => ({ time: p.date, value: p.equity })))

    const baseline = chart.addSeries(LineSeries, {
      color: CHART_COLORS.bb,
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    baseline.setData(points.map((p) => ({ time: p.date, value: startingCash })))
    chart.timeScale().fitContent()

    return () => chart.remove()
  }, [points, startingCash, isDark])

  if (points.length === 0) {
    return (
      <p className="py-10 text-center text-xs text-zinc-400 dark:text-zinc-500">
        Your equity curve starts after the first daily settlement (around 6 PM Nepal time on trading days).
      </p>
    )
  }
  return <div ref={containerRef} className="h-56 w-full" />
}
