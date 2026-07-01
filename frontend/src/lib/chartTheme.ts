export const CHART_COLORS = {
  close: { light: '#18181b', dark: '#e4e4e7' },
  sma: '#2563eb',
  bb: '#a1a1aa',
  volume: '#a1a1aa',
  rsi: '#7c3aed',
  rsiZone: '#d4d4d8',
  macd: '#2563eb',
  macdSignal: '#f59e0b',
  macdHistPos: 'rgba(16, 185, 129, 0.55)',
  macdHistNeg: 'rgba(244, 63, 94, 0.55)',
  gridLight: '#f4f4f5',
  gridDark: '#27272a',
  textLight: '#71717a',
  textDark: '#a1a1aa',
}

export function baseScales(isDark: boolean, yBounds?: { min?: number; max?: number }) {
  return {
    x: {
      grid: { display: false },
      ticks: {
        color: isDark ? CHART_COLORS.textDark : CHART_COLORS.textLight,
        maxTicksLimit: 7,
        font: { size: 10 },
        autoSkip: true,
      },
    },
    y: {
      min: yBounds?.min,
      max: yBounds?.max,
      grid: { color: isDark ? CHART_COLORS.gridDark : CHART_COLORS.gridLight },
      ticks: { color: isDark ? CHART_COLORS.textDark : CHART_COLORS.textLight, font: { size: 10 } },
    },
  }
}

export function baseChartOptions(isDark: boolean, yBounds?: { min?: number; max?: number }) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    animation: false as const,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: isDark ? '#18181b' : '#ffffff',
        titleColor: isDark ? '#f4f4f5' : '#18181b',
        bodyColor: isDark ? '#d4d4d8' : '#3f3f46',
        borderColor: isDark ? '#3f3f46' : '#e4e4e7',
        borderWidth: 1,
        padding: 8,
        boxPadding: 3,
        titleFont: { size: 11 },
        bodyFont: { size: 11 },
      },
    },
    scales: baseScales(isDark, yBounds),
  }
}
