import { GraduationCap } from 'lucide-react'

export function PaperDisclaimer() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300">
      <GraduationCap className="mt-0.5 h-4 w-4 shrink-0" />
      <p>
        Educational simulation with virtual money. Prices are real NEPSE data, but no real orders are placed.
        This is not investment advice.
      </p>
    </div>
  )
}
