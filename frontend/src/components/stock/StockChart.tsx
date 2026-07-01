import {
  CandlestickSeries,
  CrosshairMode,
  HistogramSeries,
  type IChartApi,
  LineSeries,
  createChart,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import { useTheme } from '../../hooks/useTheme'
import { CHART_COLORS } from '../../lib/chartTheme'
import type { StockDetail } from '../../types'

function LegendRow({ items }: { items: Array<{ color: string; label: string; dashed?: boolean }> }) {
  return (
    <div className="mb-1 flex flex-wrap gap-3 text-[11px] text-zinc-500 dark:text-zinc-400">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-0.5 w-3"
            style={{ backgroundColor: item.dashed ? 'transparent' : item.color, borderTop: item.dashed ? `1.5px dashed ${item.color}` : undefined }}
          />
          {item.label}
        </span>
      ))}
    </div>
  )
}

const UP_COLOR = '#10b981'
const DOWN_COLOR = '#f43f5e'

export function StockChart({ detail }: { detail: StockDetail }) {
  const { isDark } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const textColor = isDark ? CHART_COLORS.textDark : CHART_COLORS.textLight
    const gridColor = isDark ? CHART_COLORS.gridDark : CHART_COLORS.gridLight

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: 'transparent' },
        textColor,
        panes: { separatorColor: gridColor },
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor, timeVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
    })
    chartRef.current = chart

    // Pane 0: price candles + SMA20 + Bollinger bands
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderVisible: false,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    }, 0)
    candleSeries.setData(
      detail.candles
        .filter((c) => c.o !== null && c.h !== null && c.l !== null && c.c !== null)
        .map((c) => ({ time: c.t, open: c.o as number, high: c.h as number, low: c.l as number, close: c.c as number }))
    )

    const smaSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.sma,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 0)
    smaSeries.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.sma20[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
    )

    const bbUpper = chart.addSeries(LineSeries, {
      color: CHART_COLORS.bb,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 0)
    bbUpper.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.bb_upper[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
    )

    const bbLower = chart.addSeries(LineSeries, {
      color: CHART_COLORS.bb,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 0)
    bbLower.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.bb_lower[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
    )

    // Pane 1: volume
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: CHART_COLORS.volume,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 1)
    volumeSeries.setData(
      detail.candles
        .filter((c) => c.v !== null)
        .map((c) => ({
          time: c.t,
          value: c.v as number,
          color: (c.c ?? 0) >= (c.o ?? 0) ? 'rgba(16, 185, 129, 0.5)' : 'rgba(244, 63, 94, 0.5)',
        }))
    )

    // Pane 2: RSI
    const rsiSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.rsi,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 2)
    rsiSeries.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.rsi[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
    )
    rsiSeries.createPriceLine({ price: 70, color: CHART_COLORS.rsiZone, lineWidth: 1, lineStyle: 2, axisLabelVisible: false })
    rsiSeries.createPriceLine({ price: 30, color: CHART_COLORS.rsiZone, lineWidth: 1, lineStyle: 2, axisLabelVisible: false })

    // Pane 3: MACD
    const macdHistSeries = chart.addSeries(HistogramSeries, {
      priceLineVisible: false,
      lastValueVisible: false,
    }, 3)
    macdHistSeries.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.macd_hist[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
        .map((d) => ({ ...d, color: d.value >= 0 ? CHART_COLORS.macdHistPos : CHART_COLORS.macdHistNeg }))
    )

    const macdLineSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.macd,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 3)
    macdLineSeries.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.macd[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
    )

    const macdSignalSeries = chart.addSeries(LineSeries, {
      color: CHART_COLORS.macdSignal,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 3)
    macdSignalSeries.setData(
      detail.indicators.dates
        .map((t, i) => ({ time: t, value: detail.indicators.macd_sig[i] }))
        .filter((d): d is { time: string; value: number } => d.value !== null)
    )

    const panes = chart.panes()
    panes[0]?.setStretchFactor(4)
    panes[1]?.setStretchFactor(1.2)
    panes[2]?.setStretchFactor(1.5)
    panes[3]?.setStretchFactor(1.5)

    chart.timeScale().fitContent()

    return () => {
      chart.remove()
      chartRef.current = null
    }
    // Chart is fully torn down and rebuilt when the underlying data or theme changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail, isDark])

  const closeColor = isDark ? CHART_COLORS.close.dark : CHART_COLORS.close.light

  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <LegendRow
          items={[
            { color: closeColor, label: 'Candles' },
            { color: CHART_COLORS.sma, label: 'SMA 20' },
            { color: CHART_COLORS.bb, label: 'Bollinger bands', dashed: true },
            { color: CHART_COLORS.volume, label: 'Volume' },
            { color: CHART_COLORS.rsi, label: 'RSI 14' },
            { color: CHART_COLORS.macd, label: 'MACD' },
            { color: CHART_COLORS.macdSignal, label: 'Signal' },
          ]}
        />
      </div>
      <div ref={containerRef} className="h-[560px] w-full" />
    </div>
  )
}
