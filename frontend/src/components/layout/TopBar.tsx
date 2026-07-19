import { Moon, MoreVertical, Sun } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useStocksContext } from '../../context/StocksContext'
import { useTheme } from '../../hooks/useTheme'
import { MODEL_FAMILIES } from '../../hooks/useModelFamily'
import { formatRelativeTime } from '../../lib/format'
import { SearchInput } from '../ui/SearchInput'

export function TopBar() {
  const { family, setFamily, lastUpdated } = useStocksContext()
  const { isDark, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const onClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [menuOpen])

  return (
    <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/95">
      <div className="flex h-14 items-center gap-3 px-4 sm:gap-4 sm:px-6">
        <div className="flex min-w-0 items-baseline gap-2">
          <span className="whitespace-nowrap text-sm font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            NEPSE Signal Desk
          </span>
          <span className="hidden whitespace-nowrap text-xs text-zinc-400 dark:text-zinc-500 md:inline">
            Updated {formatRelativeTime(lastUpdated)}
          </span>
        </div>

        <div className="flex-1" />

        <div className="hidden shrink-0 items-center gap-0.5 rounded-md border border-zinc-200 bg-zinc-50 p-0.5 dark:border-zinc-800 dark:bg-zinc-900 sm:flex">
          {MODEL_FAMILIES.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setFamily(opt.value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                family === opt.value
                  ? 'bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-50'
                  : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
              title={opt.label}
            >
              {opt.shortLabel}
            </button>
          ))}
        </div>

        <SearchInput />

        {user ? (
          <button
            onClick={logout}
            className="hidden shrink-0 truncate text-xs font-medium text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 sm:inline"
            title={`Log out ${user.email}`}
          >
            Log out
          </button>
        ) : (
          <Link
            to="/login"
            className="hidden shrink-0 text-xs font-medium text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 sm:inline"
          >
            Log in
          </Link>
        )}

        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="shrink-0 rounded-md border border-zinc-200 p-1.5 text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-200"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>

        <div className="relative shrink-0 sm:hidden" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="More options"
            aria-expanded={menuOpen}
            className="rounded-md border border-zinc-200 p-1.5 text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-900 dark:hover:text-zinc-200"
          >
            <MoreVertical className="h-4 w-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full z-30 mt-2 w-48 rounded-md border border-zinc-200 bg-white p-2 shadow-lg dark:border-zinc-800 dark:bg-zinc-900">
              <p className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wide text-zinc-400 dark:text-zinc-500">
                Model
              </p>
              <div className="mb-2 flex flex-col gap-0.5">
                {MODEL_FAMILIES.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => {
                      setFamily(opt.value)
                      setMenuOpen(false)
                    }}
                    className={`rounded px-2 py-1.5 text-left text-sm font-medium transition-colors ${
                      family === opt.value
                        ? 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50'
                        : 'text-zinc-500 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/60'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              <div className="border-t border-zinc-200 pt-2 dark:border-zinc-800">
                {user ? (
                  <button
                    onClick={() => {
                      logout()
                      setMenuOpen(false)
                    }}
                    className="w-full rounded px-2 py-1.5 text-left text-sm font-medium text-zinc-500 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/60"
                  >
                    Log out
                  </button>
                ) : (
                  <Link
                    to="/login"
                    onClick={() => setMenuOpen(false)}
                    className="block rounded px-2 py-1.5 text-sm font-medium text-zinc-500 hover:bg-zinc-50 dark:text-zinc-400 dark:hover:bg-zinc-800/60"
                  >
                    Log in
                  </Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
