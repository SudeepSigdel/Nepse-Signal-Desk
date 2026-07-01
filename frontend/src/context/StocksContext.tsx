import { createContext, useContext, type ReactNode } from 'react'
import { useModelFamily } from '../hooks/useModelFamily'
import { useStocks } from '../hooks/useStocks'
import type { ModelFamily, Stock } from '../types'

interface StocksContextValue {
  stocks: Stock[]
  count: number
  loading: boolean
  error: string | null
  lastUpdated: number | null
  refresh: () => void
  family: ModelFamily
  setFamily: (family: ModelFamily) => void
}

const StocksContext = createContext<StocksContextValue | null>(null)

/**
 * Single shared /api/stocks feed for the whole app (dashboard table, top-bar
 * search, watchlist, portfolio signal lookups) so pages don't each poll the
 * endpoint independently, and "last updated" reflects one true refresh clock.
 */
export function StocksProvider({ children }: { children: ReactNode }) {
  const [family, setFamily] = useModelFamily()
  const { stocks, count, loading, error, lastUpdated, refresh } = useStocks(family)

  const value: StocksContextValue = { stocks, count, loading, error, lastUpdated, refresh, family, setFamily }
  return <StocksContext.Provider value={value}>{children}</StocksContext.Provider>
}

export function useStocksContext() {
  const ctx = useContext(StocksContext)
  if (!ctx) throw new Error('useStocksContext must be used within StocksProvider')
  return ctx
}
