import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'
import { useAuth } from './AuthContext'
import {
  addWatchlistSymbol,
  createHolding,
  deleteHolding,
  fetchHoldings,
  fetchWatchlist,
  removeWatchlistSymbol,
} from '../lib/api'
import type { Holding, HoldingRecord } from '../types'

const LOCAL_WATCHLIST_KEY = 'nsd_watchlist_v1'
const LOCAL_POSITIONS_KEY = 'nsd_positions_v1'

function readLocalWatchlist(): string[] {
  try {
    const raw = localStorage.getItem(LOCAL_WATCHLIST_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function readLocalHoldings(): Holding[] {
  try {
    const raw = localStorage.getItem(LOCAL_POSITIONS_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function clearLocalData() {
  try {
    localStorage.removeItem(LOCAL_WATCHLIST_KEY)
    localStorage.removeItem(LOCAL_POSITIONS_KEY)
  } catch {
    // Storage can fail in private/restricted browser contexts.
  }
}

function toHolding(record: HoldingRecord): Holding {
  return {
    id: String(record.id),
    symbol: record.symbol,
    entryDate: record.entry_date,
    entryPrice: record.entry_price,
    quantity: record.quantity,
    createdAt: new Date(record.created_at).getTime(),
  }
}

interface UserDataContextValue {
  symbols: string[]
  isWatched: (symbol: string) => boolean
  toggleWatch: (symbol: string) => void
  removeWatch: (symbol: string) => void
  holdings: Holding[]
  addHolding: (input: Omit<Holding, 'id' | 'createdAt'>) => void
  removeHolding: (id: string) => void
  loading: boolean
}

const UserDataContext = createContext<UserDataContextValue | null>(null)

/**
 * Server-persisted watchlist/holdings for the logged-in user, shared across
 * the whole app (dashboard star buttons, watchlist page, portfolio page) so
 * they don't each hit the API independently. On the first load after login,
 * any pre-existing browser-local data (from before accounts existed) is
 * imported into the account once, then cleared.
 */
export function UserDataProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  const [symbols, setSymbols] = useState<string[]>([])
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [loading, setLoading] = useState(false)
  const migratedRef = useRef(false)

  useEffect(() => {
    if (!isAuthenticated) {
      setSymbols([])
      setHoldings([])
      migratedRef.current = false
      return
    }

    let cancelled = false
    setLoading(true)

    async function loadAndMigrate() {
      if (!migratedRef.current) {
        migratedRef.current = true
        const localSymbols = readLocalWatchlist()
        const localHoldings = readLocalHoldings()

        for (const sym of localSymbols) {
          await addWatchlistSymbol(sym).catch(() => {})
        }
        for (const h of localHoldings) {
          await createHolding({
            symbol: h.symbol,
            entry_date: h.entryDate,
            entry_price: h.entryPrice,
            quantity: h.quantity,
          }).catch(() => {})
        }
        if (localSymbols.length || localHoldings.length) {
          clearLocalData()
        }
      }

      const [watchlistRes, holdingsRes] = await Promise.all([fetchWatchlist(), fetchHoldings()])
      if (cancelled) return
      setSymbols(watchlistRes.map((w) => w.symbol))
      setHoldings(holdingsRes.map(toHolding))
      setLoading(false)
    }

    loadAndMigrate().catch(() => {
      if (!cancelled) setLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [isAuthenticated])

  const isWatched = useCallback((symbol: string) => symbols.includes(symbol.toUpperCase()), [symbols])

  const toggleWatch = useCallback(
    (symbol: string) => {
      const sym = symbol.toUpperCase()
      const has = isWatched(sym)
      setSymbols((current) => (has ? current.filter((s) => s !== sym) : [...current, sym]))
      const request = has ? removeWatchlistSymbol(sym) : addWatchlistSymbol(sym)
      request.catch(() => {})
    },
    [isWatched]
  )

  const removeWatch = useCallback((symbol: string) => {
    const sym = symbol.toUpperCase()
    setSymbols((current) => current.filter((s) => s !== sym))
    removeWatchlistSymbol(sym).catch(() => {})
  }, [])

  const addHolding = useCallback((input: Omit<Holding, 'id' | 'createdAt'>) => {
    createHolding({
      symbol: input.symbol,
      entry_date: input.entryDate,
      entry_price: input.entryPrice,
      quantity: input.quantity,
    })
      .then((record) => setHoldings((current) => [...current, toHolding(record)]))
      .catch(() => {})
  }, [])

  const removeHolding = useCallback((id: string) => {
    setHoldings((current) => current.filter((h) => h.id !== id))
    deleteHolding(Number(id)).catch(() => {})
  }, [])

  const value: UserDataContextValue = {
    symbols,
    isWatched,
    toggleWatch,
    removeWatch,
    holdings,
    addHolding,
    removeHolding,
    loading,
  }

  return <UserDataContext.Provider value={value}>{children}</UserDataContext.Provider>
}

export function useUserData() {
  const ctx = useContext(UserDataContext)
  if (!ctx) throw new Error('useUserData must be used within UserDataProvider')
  return ctx
}
