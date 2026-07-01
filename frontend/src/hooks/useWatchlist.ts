import { useUserData } from '../context/UserDataContext'

/** Watchlist is now account-persisted (see UserDataContext); this keeps the old call shape. */
export function useWatchlist() {
  const { symbols, isWatched, toggleWatch, removeWatch } = useUserData()
  return { symbols, isWatched, toggle: toggleWatch, remove: removeWatch }
}
