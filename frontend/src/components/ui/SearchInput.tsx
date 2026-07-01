import { Search, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStocksContext } from '../../context/StocksContext'
import { useDebouncedValue } from '../../hooks/useDebouncedValue'
import { formatConfidence, formatPrice } from '../../lib/format'
import { getVerdictMeta } from '../../lib/verdict'

export function SearchInput() {
  const { stocks } = useStocksContext()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const debouncedQuery = useDebouncedValue(query, 120)

  const matches = useMemo(() => {
    const q = debouncedQuery.trim().toUpperCase()
    if (!q) return []
    return stocks.filter((s) => s.symbol.toUpperCase().includes(q)).slice(0, 8)
  }, [debouncedQuery, stocks])

  const goToSymbol = (symbol: string) => {
    navigate(`/stocks/${symbol}`)
    setQuery('')
    setOpen(false)
    inputRef.current?.blur()
  }

  return (
    <div className="relative w-full max-w-xs">
      <div className="flex items-center gap-2 rounded-md border border-zinc-200 bg-white px-2.5 py-1.5 focus-within:border-blue-400 dark:border-zinc-800 dark:bg-zinc-900">
        <Search className="h-3.5 w-3.5 shrink-0 text-zinc-400" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          placeholder="Search symbol…"
          className="w-full min-w-0 bg-transparent text-sm text-zinc-900 outline-none placeholder:text-zinc-400 dark:text-zinc-100"
          onChange={(e) => {
            setQuery(e.target.value)
            setOpen(true)
            setHighlighted(0)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              setHighlighted((h) => Math.min(h + 1, matches.length - 1))
            } else if (e.key === 'ArrowUp') {
              e.preventDefault()
              setHighlighted((h) => Math.max(h - 1, 0))
            } else if (e.key === 'Enter' && matches[highlighted]) {
              goToSymbol(matches[highlighted].symbol)
            } else if (e.key === 'Escape') {
              setOpen(false)
              inputRef.current?.blur()
            }
          }}
        />
        {query && (
          <button
            type="button"
            className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              setQuery('')
              inputRef.current?.focus()
            }}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {open && matches.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 max-h-80 overflow-y-auto rounded-md border border-zinc-200 bg-white shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
          {matches.map((stock, idx) => {
            const meta = getVerdictMeta(stock.verdict)
            return (
              <button
                key={stock.symbol}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => goToSymbol(stock.symbol)}
                className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm ${
                  idx === highlighted ? 'bg-zinc-100 dark:bg-zinc-800' : 'hover:bg-zinc-50 dark:hover:bg-zinc-800/60'
                }`}
              >
                <span className="font-medium text-zinc-900 dark:text-zinc-100">{stock.symbol}</span>
                <span className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                  <span className="tabular-nums">{formatPrice(stock.close)}</span>
                  <span className={`rounded px-1.5 py-0.5 font-medium ${meta.text} ${meta.bg}`}>
                    {formatConfidence(stock.confidence)}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
