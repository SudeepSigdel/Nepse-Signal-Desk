import { Briefcase, LayoutGrid, ShieldCheck, Star, TrendingUp } from 'lucide-react'
import type { ComponentType } from 'react'

export interface NavItem {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  end?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutGrid, end: true },
  { to: '/markets', label: 'Markets', icon: TrendingUp },
  { to: '/watchlist', label: 'Watchlist', icon: Star },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { to: '/trust', label: 'Model Trust', icon: ShieldCheck },
]
