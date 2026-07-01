import { fetchModelPerformance } from '../lib/api'
import { usePolling } from './usePolling'

export function useModelPerformance(family: string) {
  const { data, loading, error, refresh } = usePolling(() => fetchModelPerformance(family), [family])
  return { performance: data, loading, error, refresh }
}
