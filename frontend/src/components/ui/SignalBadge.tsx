import { getVerdictMeta } from '../../lib/verdict'

export function SignalBadge({ verdict, className = '' }: { verdict: string | null | undefined; className?: string }) {
  const meta = getVerdictMeta(verdict)
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded border px-1.5 py-0.5 text-xs font-medium ${meta.text} ${meta.bg} ${meta.border} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  )
}
