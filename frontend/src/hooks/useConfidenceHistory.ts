import { useEffect, useState } from 'react'
import type { ConfidenceLogEntry } from '../types'

const STORAGE_PREFIX = 'nsd_conf_log_'
const MAX_ENTRIES = 120

function storageKey(symbol: string) {
  return `${STORAGE_PREFIX}${symbol.toUpperCase()}`
}

function readLog(symbol: string): ConfidenceLogEntry[] {
  try {
    const raw = localStorage.getItem(storageKey(symbol))
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeLog(symbol: string, entries: ConfidenceLogEntry[]) {
  try {
    localStorage.setItem(storageKey(symbol), JSON.stringify(entries.slice(-MAX_ENTRIES)))
  } catch {
    // Storage can fail in private/restricted browser contexts.
  }
}

/**
 * The backend does not persist historical confidence scores — only the current
 * signal. This records one observation per calendar day per symbol as the user
 * actually views it, building an honest, locally-observed confidence history
 * rather than fabricating one.
 */
export function useConfidenceHistory(
  symbol: string,
  confidence: number | null,
  verdict: string | null,
  date: string | null
): ConfidenceLogEntry[] {
  const [entries, setEntries] = useState<ConfidenceLogEntry[]>(() => (symbol ? readLog(symbol) : []))

  useEffect(() => {
    setEntries(symbol ? readLog(symbol) : [])
  }, [symbol])

  useEffect(() => {
    if (!symbol || confidence === null || !date || !verdict) return
    const existing = readLog(symbol)
    if (existing.some((e) => e.date === date)) return

    const next = [...existing, { timestamp: Date.now(), date, confidence, verdict }].sort((a, b) =>
      a.date.localeCompare(b.date)
    )
    writeLog(symbol, next)
    setEntries(next)
  }, [symbol, confidence, verdict, date])

  return entries
}
