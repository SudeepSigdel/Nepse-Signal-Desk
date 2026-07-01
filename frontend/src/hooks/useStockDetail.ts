import { fetchStockDetail } from '../lib/api'
import { usePolling } from './usePolling'

export function useStockDetail(symbol: string, days: number = 180) {
  const { data, loading, error, lastUpdated, refresh } = usePolling(
    () => fetchStockDetail(symbol, days),
    [symbol, days],
    null
  )

  return { detail: data, loading, error, lastUpdated, refresh }
}
