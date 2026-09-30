import { Bot, Briefcase, LayoutGrid, ShieldCheck, Star, TrendingUp, Wallet } from 'lucide-react'
import type { ComponentType } from 'react'

export interface NavItem {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  end?: boolean
  /** Shorter label for the mobile bottom bar. */
  short?: string
  /** Mobile placement: a bottom-bar tab, or inside the "More" sheet. */
  mobile: 'primary' | 'more'
}

export const NAV_ITEMS: NavItem[] = [
  { to: '/', label: 'Dashboard', short: 'Home', icon: LayoutGrid, end: true, mobile: 'primary' },
  { to: '/markets', label: 'Markets', icon: TrendingUp, mobile: 'primary' },
  { to: '/watchlist', label: 'Watchlist', icon: Star, mobile: 'more' },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase, mobile: 'more' },
  { to: '/paper', label: 'Paper Trade', short: 'Trade', icon: Wallet, mobile: 'primary' },
  { to: '/agents', label: 'Agents', short: 'Bots', icon: Bot, mobile: 'primary' },
  { to: '/trust', label: 'Model Trust', icon: ShieldCheck, mobile: 'more' },
]
