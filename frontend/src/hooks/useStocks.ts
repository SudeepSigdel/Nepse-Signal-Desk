import axios from 'axios'
import { useState, useEffect } from 'react'
import { API_BASE_URL } from '../config'

const CACHE_TTL_MS = 5 * 60 * 1000

type CacheEntry<T> = {
  data: T
  timestamp: number
}

const stocksCache: { entry: CacheEntry<Stock[]> | null } = { entry: null }
const stockDetailCache = new Map<string, CacheEntry<StockDetail>>()
const signalCache = new Map<string, CacheEntry<SignalDetail>>()

export interface Stock {
  symbol: string
  date: string
  close: number
  rsi: number | null
  confidence: number
  buy_confidence?: number
  sell_confidence?: number | null
  tier: string
  verdict?: string
}

export interface ApiStock {
  Symbol: string
  Date: string
  Close: number | null
  rsi?: number | null
  confidence: number
  buy_confidence?: number
  sell_confidence?: number | null
  Tier: string
  verdict?: string
}

export interface StockResponse {
  stocks: ApiStock[]
  count: number
}

const normalizeStock = (stock: ApiStock): Stock => ({
  symbol: stock.Symbol,
  date: stock.Date,
  close: stock.Close ?? 0,
  rsi: stock.rsi ?? null,
  confidence: stock.confidence,
  buy_confidence: stock.buy_confidence ?? stock.confidence,
  sell_confidence: stock.sell_confidence ?? null,
  tier: stock.Tier,
  verdict: stock.verdict,
})

export const useStocks = (refreshInterval: number = 30000) => {
  const [stocks, setStocks] = useState<Stock[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const fetchStocks = async () => {
      try {
        setLoading(true)

        if (stocksCache.entry && Date.now() - stocksCache.entry.timestamp < CACHE_TTL_MS) {
          setStocks(stocksCache.entry.data)
          setError(null)
          return
        }

        const response = await axios.get<StockResponse>(`${API_BASE_URL}/api/stocks`)
        const normalized = response.data.stocks.map(normalizeStock)
        if (!cancelled) {
          setStocks(normalized)
          setError(null)
        }
        // Update cache after a successful fetch
        stocksCache.entry = {
          data: normalized,
          timestamp: Date.now(),
        }
      } catch (err) {
        console.error('Error fetching stocks:', err)
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch stocks')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchStocks()
    const interval = setInterval(fetchStocks, refreshInterval)

    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [refreshInterval])

  return { stocks, loading, error }
}

export interface StockDetail {
  symbol: string
  days: number
  candles: Array<{
    t: string
    o: number | null
    h: number | null
    l: number | null
    c: number | null
    v: number | null
  }>
  indicators: {
    sma20: (number | null)[]
    bb_upper: (number | null)[]
    bb_lower: (number | null)[]
    bb_mid: (number | null)[]
    ema12: (number | null)[]
    ema26: (number | null)[]
    rsi: (number | null)[]
    macd: (number | null)[]
    macd_sig: (number | null)[]
    macd_hist: (number | null)[]
    volume: (number | null)[]
    dates: string[]
  }
}

export const useStockDetail = (symbol: string, days: number = 180) => {
  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!symbol) return

    let cancelled = false
    const cacheKey = `${symbol.toUpperCase()}:${days}`

    const fetchDetail = async () => {
      try {
        setLoading(true)
        const cached = stockDetailCache.get(cacheKey)
        if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
          setDetail(cached.data)
          setError(null)
          return
        }

        const response = await axios.get<StockDetail>(
          `${API_BASE_URL}/api/stocks/${symbol}`,
          { params: { days } }
        )
        if (!cancelled) {
          setDetail(response.data)
          setError(null)
        }
        stockDetailCache.set(cacheKey, { data: response.data, timestamp: Date.now() })
      } catch (err) {
        console.error('Error fetching stock detail:', err)
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch details')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchDetail()
    return () => {
      cancelled = true
    }
  }, [symbol, days])

  return { detail, loading, error }
}

export interface SignalDetail {
  symbol: string
  date: string
  close: number
  confidence: number
  verdict: string
  verdict_color: string
  description: string
  active_signals: string[]
  indicators: {
    rsi: number | null
    rsi_zone: string
    macd: number | null
    macd_signal: number | null
    macd_hist: number
    macd_bias: string
    bb_pctb: number | null
    bb_zone: string
    in_uptrend: boolean
    volume_ratio: number | null
    volume_note: string
  }
  thresholds: {
    recommended: number
    minimum: number
  }
}

export const useSignal = (symbol: string) => {
  const [signal, setSignal] = useState<SignalDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!symbol) return

    let cancelled = false
    const cacheKey = symbol.toUpperCase()

    const fetchSignal = async () => {
      try {
        setLoading(true)
        const cached = signalCache.get(cacheKey)
        if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
          setSignal(cached.data)
          setError(null)
          return
        }

        const response = await axios.get<SignalDetail>(`${API_BASE_URL}/api/signal/${symbol}`)
        if (!cancelled) {
          setSignal(response.data)
          setError(null)
        }
        signalCache.set(cacheKey, { data: response.data, timestamp: Date.now() })
      } catch (err) {
        console.error('Error fetching signal:', err)
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to fetch signal')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchSignal()
    return () => {
      cancelled = true
    }
  }, [symbol])

  return { signal, loading, error }
}
