import { AlertTriangle } from 'lucide-react'

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-rose-200 bg-rose-50 px-6 py-12 text-center dark:border-rose-500/30 dark:bg-rose-500/10">
      <AlertTriangle className="h-6 w-6 text-rose-500" />
      <p className="text-sm font-medium text-rose-700 dark:text-rose-300">Couldn't load data</p>
      <p className="max-w-sm text-xs text-rose-600/80 dark:text-rose-400/80">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 rounded-md border border-rose-300 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 dark:border-rose-500/40 dark:text-rose-300 dark:hover:bg-rose-500/20"
        >
          Retry
        </button>
      )}
    </div>
  )
}
