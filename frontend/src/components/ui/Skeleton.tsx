export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse rounded bg-zinc-200 dark:bg-zinc-800 ${className}`} />
}

export function TableRowSkeleton({ columns = 6 }: { columns?: number }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-3 py-3">
          <Skeleton className="h-4 w-full max-w-[6rem]" />
        </td>
      ))}
    </tr>
  )
}
