import { useMemo } from 'react'
import { REFRESH_INTERVAL_MS } from '../config'
import { fetchStocks } from '../lib/api'
import type { Stock } from '../types'
import { usePolling } from './usePolling'

export function useStocks(family?: string) {
  const { data, loading, error, lastUpdated, refresh } = usePolling(
    () => fetchStocks(family),
    [family],
    REFRESH_INTERVAL_MS
  )

  const stocks: Stock[] = useMemo(() => data?.stocks ?? [], [data])

  return { stocks, count: data?.count ?? 0, loading, error, lastUpdated, refresh }
}
