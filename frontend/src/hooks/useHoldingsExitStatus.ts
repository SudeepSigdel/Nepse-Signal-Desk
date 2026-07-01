import { useEffect, useState } from 'react'
import { checkPositionExit } from '../lib/api'
import type { ExitStatusResponse, Holding, Stock } from '../types'

/** Computes live exit guidance per holding via POST /api/positions/exit-check, keyed by holding id. */
export function useHoldingsExitStatus(holdings: Holding[], stocks: Stock[]) {
  const [statusMap, setStatusMap] = useState<Record<string, ExitStatusResponse>>({})

  useEffect(() => {
    let cancelled = false

    holdings.forEach(async (holding) => {
      const stock = stocks.find((s) => s.symbol === holding.symbol)
      if (!stock || stock.close === null) return
      const buyConfidence = stock.buy_confidence ?? stock.confidence

      try {
        const result = await checkPositionExit({
          symbol: holding.symbol,
          entry_date: holding.entryDate,
          entry_price: holding.entryPrice,
          current_price: stock.close,
          current_buy_conf: buyConfidence,
        })
        if (!cancelled) {
          setStatusMap((prev) => ({ ...prev, [holding.id]: result }))
        }
      } catch {
        // Leave any previous status in place; row falls back to basic P/L display.
      }
    })

    return () => {
      cancelled = true
    }
  }, [holdings, stocks])

  return statusMap
}
