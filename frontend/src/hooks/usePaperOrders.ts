import { REFRESH_INTERVAL_MS } from '../config'
import { fetchPaperOrders } from '../lib/api'
import type { PaperOrder } from '../types'
import { usePolling } from './usePolling'

export function usePaperOrders(accountId: number | null) {
  const { data, loading, error, refresh } = usePolling<PaperOrder[]>(
    () => (accountId ? fetchPaperOrders(accountId) : Promise.resolve([])),
    [accountId],
    REFRESH_INTERVAL_MS
  )
  return { orders: data ?? [], loading, error, refresh }
}
