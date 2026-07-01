import { useCallback, useState } from 'react'
import { checkPositionExit } from '../lib/api'
import type { ExitStatusResponse, PositionCheckRequest } from '../types'

export function useExitCheck() {
  const [result, setResult] = useState<ExitStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const check = useCallback(async (payload: PositionCheckRequest) => {
    setLoading(true)
    setError(null)
    try {
      const data = await checkPositionExit(payload)
      setResult(data)
      return data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check position')
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  return { result, loading, error, check }
}
