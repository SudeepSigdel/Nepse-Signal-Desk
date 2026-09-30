import { useEffect, useState } from 'react'
import { fetchFeePreview } from '../lib/api'
import type { FeeBreakdown, FeePreviewRequest } from '../types'
import { useDebouncedValue } from './useDebouncedValue'

/** Itemized NEPSE costs for a prospective order, refreshed as the ticket changes. */
export function useFeePreview(request: FeePreviewRequest | null) {
  const debounced = useDebouncedValue(request, 250)
  const key = debounced ? JSON.stringify(debounced) : ''
  const [preview, setPreview] = useState<FeeBreakdown | null>(null)

  useEffect(() => {
    if (!debounced) {
      setPreview(null)
      return
    }
    let cancelled = false
    fetchFeePreview(debounced)
      .then((result) => !cancelled && setPreview(result))
      .catch(() => !cancelled && setPreview(null))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  return preview
}
