import {
  CandlestickSeries,
  CrosshairMode,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
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

// How close to the left edge (in bars) the visible range must get before we fetch an older page.
const LOAD_MORE_THRESHOLD_BARS = 20

interface SeriesRefs {
  candle: ISeriesApi<'Candlestick'>
  sma: ISeriesApi<'Line'>
  bbUpper: ISeriesApi<'Line'>
  bbLower: ISeriesApi<'Line'>
  volume: ISeriesApi<'Histogram'>
  rsi: ISeriesApi<'Line'>
  macdHist: ISeriesApi<'Histogram'>
  macdLine: ISeriesApi<'Line'>
  macdSignal: ISeriesApi<'Line'>
}

function toCandles(detail: StockDetail) {
  return detail.candles
    .filter((c) => c.o !== null && c.h !== null && c.l !== null && c.c !== null)
    .map((c) => ({ time: c.t, open: c.o as number, high: c.h as number, low: c.l as number, close: c.c as number }))
}

function toVolume(detail: StockDetail) {
  return detail.candles
    .filter((c) => c.v !== null)
    .map((c) => ({
      time: c.t,
      value: c.v as number,
      color: (c.c ?? 0) >= (c.o ?? 0) ? 'rgba(16, 185, 129, 0.5)' : 'rgba(244, 63, 94, 0.5)',
    }))
}

function toLine(dates: string[], values: Array<number | null>) {
  return dates
    .map((t, i) => ({ time: t, value: values[i] }))
    .filter((d): d is { time: string; value: number } => d.value !== null)
}

function toMacdHist(dates: string[], values: Array<number | null>) {
  return dates
    .map((t, i) => ({ time: t, value: values[i] }))
    .filter((d): d is { time: string; value: number } => d.value !== null)
    .map((d) => ({ ...d, color: d.value >= 0 ? CHART_COLORS.macdHistPos : CHART_COLORS.macdHistNeg }))
}

function applyData(series: SeriesRefs, detail: StockDetail) {
  series.candle.setData(toCandles(detail))
  series.sma.setData(toLine(detail.indicators.dates, detail.indicators.sma20))
  series.bbUpper.setData(toLine(detail.indicators.dates, detail.indicators.bb_upper))
  series.bbLower.setData(toLine(detail.indicators.dates, detail.indicators.bb_lower))
  series.volume.setData(toVolume(detail))
  series.rsi.setData(toLine(detail.indicators.dates, detail.indicators.rsi))
  series.macdHist.setData(toMacdHist(detail.indicators.dates, detail.indicators.macd_hist))
  series.macdLine.setData(toLine(detail.indicators.dates, detail.indicators.macd))
  series.macdSignal.setData(toLine(detail.indicators.dates, detail.indicators.macd_sig))
}

interface StockChartProps {
  detail: StockDetail
  loadingMore?: boolean
  hasMore?: boolean
  onLoadMore?: () => void
}

export function StockChart({ detail, loadingMore, hasMore, onLoadMore }: StockChartProps) {
  const { isDark } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<SeriesRefs | null>(null)
  const prevCandleCountRef = useRef(0)
  const hasMoreRef = useRef(hasMore)
  const loadingMoreRef = useRef(loadingMore)
  const onLoadMoreRef = useRef(onLoadMore)
  hasMoreRef.current = hasMore
  loadingMoreRef.current = loadingMore
  onLoadMoreRef.current = onLoadMore

  // Create the chart and series once (and on theme change). Data is applied separately below
  // so that paging in older history doesn't tear down and refit the whole chart.
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

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      borderVisible: false,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
    }, 0)

    const sma = chart.addSeries(LineSeries, {
      color: CHART_COLORS.sma,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 0)

    const bbUpper = chart.addSeries(LineSeries, {
      color: CHART_COLORS.bb,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 0)

    const bbLower = chart.addSeries(LineSeries, {
      color: CHART_COLORS.bb,
      lineWidth: 1,
      lineStyle: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 0)

    const volume = chart.addSeries(HistogramSeries, {
      color: CHART_COLORS.volume,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 1)

    const rsi = chart.addSeries(LineSeries, {
      color: CHART_COLORS.rsi,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 2)
    rsi.createPriceLine({ price: 70, color: CHART_COLORS.rsiZone, lineWidth: 1, lineStyle: 2, axisLabelVisible: false })
    rsi.createPriceLine({ price: 30, color: CHART_COLORS.rsiZone, lineWidth: 1, lineStyle: 2, axisLabelVisible: false })

    const macdHist = chart.addSeries(HistogramSeries, {
      priceLineVisible: false,
      lastValueVisible: false,
    }, 3)

    const macdLine = chart.addSeries(LineSeries, {
      color: CHART_COLORS.macd,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 3)

    const macdSignal = chart.addSeries(LineSeries, {
      color: CHART_COLORS.macdSignal,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    }, 3)

    const panes = chart.panes()
    panes[0]?.setStretchFactor(4)
    panes[1]?.setStretchFactor(1.2)
    panes[2]?.setStretchFactor(1.5)
    panes[3]?.setStretchFactor(1.5)

    seriesRef.current = { candle, sma, bbUpper, bbLower, volume, rsi, macdHist, macdLine, macdSignal }
    prevCandleCountRef.current = 0

    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range) return
      if (range.from < LOAD_MORE_THRESHOLD_BARS && hasMoreRef.current && !loadingMoreRef.current) {
        onLoadMoreRef.current?.()
      }
    })

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [isDark])

  // Push data whenever it changes. A page prepended to the front of history keeps the
  // user's current view stable instead of snapping back to fitContent().
  useEffect(() => {
    const chart = chartRef.current
    const series = seriesRef.current
    if (!chart || !series) return

    const prevCount = prevCandleCountRef.current
    const isAppend = prevCount > 0 && detail.candles.length > prevCount
    const prevRange = isAppend ? chart.timeScale().getVisibleLogicalRange() : null

    applyData(series, detail)

    if (isAppend && prevRange) {
      const added = detail.candles.length - prevCount
      chart.timeScale().setVisibleLogicalRange({ from: prevRange.from + added, to: prevRange.to + added })
    } else {
      chart.timeScale().fitContent()
    }

    prevCandleCountRef.current = detail.candles.length
  }, [detail])

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
        {loadingMore && <span className="text-[11px] text-zinc-400 dark:text-zinc-500">Loading older history…</span>}
      </div>
      <div ref={containerRef} className="h-[560px] w-full" />
    </div>
  )
}
