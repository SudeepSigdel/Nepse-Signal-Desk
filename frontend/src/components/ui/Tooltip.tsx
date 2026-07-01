import { Info } from 'lucide-react'
import { useState, type ReactNode } from 'react'

export function Tooltip({ label, children }: { label: string; children?: ReactNode }) {
  const [open, setOpen] = useState(false)

  return (
    <span className="relative inline-flex">
      {/* Span, not button: this renders inside SortableHeader's <button> in
          StockTable.tsx, and nested buttons are invalid HTML. */}
      <span
        role="button"
        tabIndex={0}
        className="inline-flex items-center text-zinc-400 hover:text-zinc-600 dark:text-zinc-500 dark:hover:text-zinc-300"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setOpen((o) => !o)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            e.stopPropagation()
            setOpen((o) => !o)
          }
        }}
        aria-label={label}
      >
        {children ?? <Info className="h-3.5 w-3.5" />}
      </span>
      {open && (
        <span
          role="tooltip"
          className="absolute top-full left-1/2 z-40 mt-1.5 w-56 -translate-x-1/2 rounded-md border border-zinc-200 bg-white p-2 text-xs leading-relaxed text-zinc-600 shadow-lg dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
        >
          {label}
        </span>
      )}
    </span>
  )
}
