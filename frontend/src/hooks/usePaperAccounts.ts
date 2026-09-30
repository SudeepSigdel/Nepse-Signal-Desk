import { useCallback, useState } from 'react'
import { REFRESH_INTERVAL_MS } from '../config'
import { createPaperAccount, fetchPaperAccounts } from '../lib/api'
import type { PaperAccount } from '../types'
import { usePolling } from './usePolling'

const SELECTED_KEY = 'paper.selectedAccountId'

function readSelected(): number | null {
  try {
    const raw = localStorage.getItem(SELECTED_KEY)
    return raw ? Number(raw) : null
  } catch {
    return null
  }
}

export const DEFAULT_STARTING_CASH = 1_000_000

/** The user's paper accounts, the one currently selected, and a way to open a first account. */
export function usePaperAccounts() {
  const { data, loading, error, refresh } = usePolling(fetchPaperAccounts, [], REFRESH_INTERVAL_MS)
  const [selectedId, setSelectedId] = useState<number | null>(readSelected)

  const accounts: PaperAccount[] = data ?? []
  const account = accounts.find((a) => a.id === selectedId) ?? accounts[0] ?? null

  const select = useCallback((id: number) => {
    setSelectedId(id)
    try {
      localStorage.setItem(SELECTED_KEY, String(id))
    } catch {
      // Storage unavailable; selection just won't persist.
    }
  }, [])

  const create = useCallback(
    async (name: string, startingCash = DEFAULT_STARTING_CASH) => {
      const created = await createPaperAccount(name, startingCash)
      select(created.id)
      refresh()
      return created
    },
    [refresh, select]
  )

  return { accounts, account, loading, error, refresh, select, create }
}
