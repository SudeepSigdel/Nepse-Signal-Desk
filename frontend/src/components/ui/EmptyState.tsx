import type { ComponentType, ReactNode } from 'react'

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: ComponentType<{ className?: string }>
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-zinc-300 px-6 py-12 text-center dark:border-zinc-700">
      {Icon && <Icon className="h-8 w-8 text-zinc-300 dark:text-zinc-600" />}
      <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">{title}</p>
      {description && <p className="max-w-sm text-xs text-zinc-500 dark:text-zinc-400">{description}</p>}
      {action}
    </div>
  )
}
