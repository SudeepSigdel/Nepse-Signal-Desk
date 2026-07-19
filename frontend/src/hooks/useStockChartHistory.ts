import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchStockDetail } from '../lib/api'
import type { StockDetail } from '../types'

const PAGE_SIZE = 250

function mergeOlderPage(older: StockDetail, current: StockDetail): StockDetail {
  return {
    symbol: current.symbol,
    days: current.candles.length + older.candles.length,
    has_more: older.has_more,
    candles: [...older.candles, ...current.candles],
    indicators: {
      sma20: [...older.indicators.sma20, ...current.indicators.sma20],
      bb_upper: [...older.indicators.bb_upper, ...current.indicators.bb_upper],
      bb_lower: [...older.indicators.bb_lower, ...current.indicators.bb_lower],
      bb_mid: [...older.indicators.bb_mid, ...current.indicators.bb_mid],
      ema12: [...older.indicators.ema12, ...current.indicators.ema12],
      ema26: [...older.indicators.ema26, ...current.indicators.ema26],
      rsi: [...older.indicators.rsi, ...current.indicators.rsi],
      macd: [...older.indicators.macd, ...current.indicators.macd],
      macd_sig: [...older.indicators.macd_sig, ...current.indicators.macd_sig],
      macd_hist: [...older.indicators.macd_hist, ...current.indicators.macd_hist],
      volume: [...older.indicators.volume, ...current.indicators.volume],
      dates: [...older.indicators.dates, ...current.indicators.dates],
    },
  }
}

/** Loads a stock's chart history a page at a time, oldest-first pagination via `loadMore`. */
export function useStockChartHistory(symbol: string) {
  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const loadedCountRef = useRef(0)
  const loadingMoreRef = useRef(false)
  const requestGenerationRef = useRef(0)
  const symbolRef = useRef(symbol)
  symbolRef.current = symbol

  const loadInitial = useCallback(() => {
    const generation = ++requestGenerationRef.current
    let cancelled = false
    loadingMoreRef.current = false
    setLoading(true)
    setLoadingMore(false)
    setError(null)

    fetchStockDetail(symbol, PAGE_SIZE, 0)
      .then((result) => {
        if (cancelled || generation !== requestGenerationRef.current) return
        setDetail(result)
        loadedCountRef.current = result.candles.length
      })
      .catch((err) => {
        if (cancelled || generation !== requestGenerationRef.current) return
        setError(err instanceof Error ? err.message : 'Request failed')
      })
      .finally(() => {
        if (!cancelled && generation === requestGenerationRef.current) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [symbol])

  useEffect(() => loadInitial(), [loadInitial])

  const loadMore = useCallback(() => {
    if (loadingMoreRef.current || !detail || !detail.has_more) return
    loadingMoreRef.current = true
    setLoadingMore(true)
    const generation = requestGenerationRef.current

    fetchStockDetail(symbol, PAGE_SIZE, loadedCountRef.current)
      .then((older) => {
        if (symbolRef.current !== symbol || generation !== requestGenerationRef.current) return
        setDetail((current) => (current ? mergeOlderPage(older, current) : current))
        loadedCountRef.current += older.candles.length
      })
      .catch((err) => {
        if (symbolRef.current !== symbol || generation !== requestGenerationRef.current) return
        setError(err instanceof Error ? err.message : 'Request failed')
      })
      .finally(() => {
        if (generation !== requestGenerationRef.current) return
        loadingMoreRef.current = false
        setLoadingMore(false)
      })
  }, [symbol, detail])

  return {
    detail,
    loading,
    loadingMore,
    hasMore: detail?.has_more ?? false,
    error,
    loadMore,
    refresh: loadInitial,
  }
}
