import { Menu } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { NavLink, matchPath, useLocation } from 'react-router-dom'
import { NAV_ITEMS } from './navItems'

const PRIMARY = NAV_ITEMS.filter((item) => item.mobile === 'primary')
const MORE = NAV_ITEMS.filter((item) => item.mobile === 'more')

const tabClass = (active: boolean) =>
  `flex flex-1 flex-col items-center gap-1 py-2 text-[11px] font-medium ${
    active ? 'text-zinc-900 dark:text-zinc-50' : 'text-zinc-400 dark:text-zinc-500'
  }`

/** Mobile tab bar: four primary sections plus a "More" sheet for the rest. */
export function BottomNav() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { pathname } = useLocation()
  const moreActive = MORE.some((item) => matchPath({ path: item.to, end: false }, pathname))

  useEffect(() => setOpen(false), [pathname])

  useEffect(() => {
    if (!open) return
    const onClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className="md:hidden">
      {open && (
        <div
          role="menu"
          className="fixed inset-x-3 bottom-16 z-30 rounded-lg border border-zinc-200 bg-white p-1 shadow-lg dark:border-zinc-800 dark:bg-zinc-900"
        >
          {MORE.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              role="menuitem"
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium ${
                  isActive
                    ? 'bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-50'
                    : 'text-zinc-600 dark:text-zinc-300'
                }`
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
      <nav className="fixed inset-x-0 bottom-0 z-20 flex border-t border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-950">
        {PRIMARY.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => tabClass(isActive)}>
            <item.icon className="h-5 w-5" />
            {item.short ?? item.label}
          </NavLink>
        ))}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-haspopup="menu"
          className={tabClass(open || moreActive)}
        >
          <Menu className="h-5 w-5" />
          More
        </button>
      </nav>
    </div>
  )
}
