import { useCallback, useEffect, useRef, useState } from 'react'

interface PollingState<T> {
  data: T | null
  loading: boolean
  error: string | null
  lastUpdated: number | null
  refresh: () => void
}

/** Fetches once immediately, then re-fetches every `intervalMs` (if set) or on `refresh()`. */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
  intervalMs: number | null = null
): PollingState<T> {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<number | null>(null)
  const [tick, setTick] = useState(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    fetcherRef
      .current()
      .then((result) => {
        if (cancelled) return
        setData(result)
        setError(null)
        setLastUpdated(Date.now())
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : 'Request failed')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    if (!intervalMs) return () => { cancelled = true }

    const id = setInterval(() => setTick((t) => t + 1), intervalMs)
    return () => {
      cancelled = true
      clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, intervalMs])

  const refresh = useCallback(() => setTick((t) => t + 1), [])

  return { data, loading, error, lastUpdated, refresh }
}
