import { REFRESH_INTERVAL_MS } from '../config'
import { fetchSignal } from '../lib/api'
import { usePolling } from './usePolling'

export function useSignal(symbol: string, family?: string) {
  const { data, loading, error, lastUpdated, refresh } = usePolling(
    () => fetchSignal(symbol, family),
    [symbol, family],
    REFRESH_INTERVAL_MS
  )

  return { signal: data, loading, error, lastUpdated, refresh }
}
