import { LineSeries, LineStyle, createChart, type ISeriesApi, type MouseEventParams, type Time } from 'lightweight-charts'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useTheme } from '../../hooks/useTheme'
import { CHART_COLORS } from '../../lib/chartTheme'
import { formatMoney } from '../../lib/format'
import type { AgentEntry } from '../../types'

// Validated categorical palette (scripts/validate_palette.js, light on #fff and dark on #18181b).
// Colors follow the agent, never its rank, so a bot keeps its color everywhere.
const AGENT_COLORS: Record<string, { light: string; dark: string }> = {
  SignalBot: { light: '#2a78d6', dark: '#3987e5' },
  TunedSignalBot: { light: '#eb6834', dark: '#d95926' },
  CoreSatellite: { light: '#1baf7a', dark: '#199e70' },
  RLBot: { light: '#eda100', dark: '#c98500' },
  RandomBot: { light: '#e87ba4', dark: '#d55181' },
  BuyAndHold: { light: '#008300', dark: '#008300' },
}
const FALLBACK = { light: '#71717a', dark: '#a1a1aa' }

export function agentColor(name: string, isDark: boolean) {
  const c = AGENT_COLORS[name] ?? FALLBACK
  return isDark ? c.dark : c.light
}

/** Equity of each agent's backtest portfolio on one Rs axis, with a crosshair read-out legend. */
export function AgentEquityChart({ agents, startingCash }: { agents: AgentEntry[]; startingCash: number }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { isDark } = useTheme()
  const [hover, setHover] = useState<{ date: string; values: Record<string, number> } | null>(null)
  const last = useMemo(
    () => Object.fromEntries(agents.map((a) => [a.name, a.equity[a.equity.length - 1]?.[1] ?? startingCash])),
    [agents, startingCash]
  )

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const textColor = isDark ? CHART_COLORS.textDark : CHART_COLORS.textLight
    const gridColor = isDark ? CHART_COLORS.gridDark : CHART_COLORS.gridLight
    const chart = createChart(container, {
      autoSize: true,
      layout: { background: { color: 'transparent' }, textColor },
      grid: { vertLines: { visible: false }, horzLines: { color: gridColor } },
      rightPriceScale: { borderColor: gridColor },
      timeScale: { borderColor: gridColor },
      localization: { priceFormatter: (v: number) => `${(v / 100000).toFixed(1)}L` },
    })
    const series = new Map<ISeriesApi<'Line'>, string>()
    for (const agent of agents) {
      const s = chart.addSeries(LineSeries, {
        color: agentColor(agent.name, isDark),
        lineWidth: 2,
        lineStyle: agent.name === 'BuyAndHold' ? LineStyle.Dashed : LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
      })
      s.setData(agent.equity.map(([t, v]) => ({ time: t, value: v })))
      series.set(s, agent.name)
    }
    chart.timeScale().fitContent()
    const onMove = (param: MouseEventParams<Time>) => {
      if (!param.time || !param.point) {
        setHover(null)
        return
      }
      const values: Record<string, number> = {}
      param.seriesData.forEach((d, s) => {
        const name = series.get(s as ISeriesApi<'Line'>)
        if (name && 'value' in d) values[name] = d.value
      })
      setHover({ date: String(param.time), values })
    }
    chart.subscribeCrosshairMove(onMove)
    return () => {
      chart.unsubscribeCrosshairMove(onMove)
      chart.remove()
    }
  }, [agents, isDark])

  const shown = hover?.values ?? last
  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="text-zinc-400 dark:text-zinc-500">{hover ? hover.date : 'Latest'}</span>
        {agents.map((a) => (
          <span key={a.name} className="inline-flex items-center gap-1.5 text-zinc-600 dark:text-zinc-300">
            <span
              className="inline-block h-0.5 w-4"
              style={
                a.name === 'BuyAndHold'
                  ? { borderTop: `2px dashed ${agentColor(a.name, isDark)}` }
                  : { backgroundColor: agentColor(a.name, isDark), height: 2 }
              }
            />
            {a.name}
            <span className="tabular-nums text-zinc-900 dark:text-zinc-100">{formatMoney(shown[a.name])}</span>
          </span>
        ))}
      </div>
      <div ref={containerRef} className="h-72 w-full" />
    </div>
  )
}
