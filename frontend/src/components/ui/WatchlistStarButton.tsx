import { Star } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useWatchlist } from '../../hooks/useWatchlist'

export function WatchlistStarButton({ symbol, size = 'md' }: { symbol: string; size?: 'sm' | 'md' }) {
  const { isAuthenticated } = useAuth()
  const { isWatched, toggle } = useWatchlist()
  const navigate = useNavigate()
  const watched = isWatched(symbol)
  const dim = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'

  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        if (!isAuthenticated) {
          navigate('/login')
          return
        }
        toggle(symbol)
      }}
      aria-label={watched ? `Remove ${symbol} from watchlist` : `Add ${symbol} to watchlist`}
      aria-pressed={watched}
      className={`inline-flex items-center justify-center rounded p-1 transition-colors ${
        watched
          ? 'text-amber-500 hover:text-amber-600'
          : 'text-zinc-300 hover:text-zinc-400 dark:text-zinc-600 dark:hover:text-zinc-400'
      }`}
    >
      <Star className={dim} fill={watched ? 'currentColor' : 'none'} />
    </button>
  )
}
