import { useEffect, useState } from 'react'
import type { Stock } from '../types'

type Baseline = Record<string, number>

function todayKey(): string {
  const d = new Date()
  return `nsd_baseline_${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`
}

function readBaseline(key: string): Baseline | null {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function writeBaseline(key: string, data: Baseline) {
  try {
    localStorage.setItem(key, JSON.stringify(data))
  } catch {
    // Storage can fail in private/restricted browser contexts.
  }
}

/**
 * The backend keeps no historical confidence log, so "improving/weakening"
 * would otherwise have nothing real to compare against. This snapshots each
 * symbol's confidence the first time it's seen today (per browser) and keeps
 * that fixed baseline for the rest of the day, so later polls can show a
 * genuine intraday delta instead of a fabricated trend.
 */
export function useConfidenceBaseline(stocks: Stock[]): Baseline {
  const [baseline, setBaseline] = useState<Baseline>({})

  useEffect(() => {
    if (stocks.length === 0) return
    const key = todayKey()
    const existing = readBaseline(key)
    if (existing) {
      setBaseline(existing)
      return
    }
    const snapshot: Baseline = {}
    for (const s of stocks) snapshot[s.symbol] = s.confidence
    writeBaseline(key, snapshot)
    setBaseline(snapshot)
  }, [stocks])

  return baseline
}
