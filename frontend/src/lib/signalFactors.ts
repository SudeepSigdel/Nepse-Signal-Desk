import type { SignalDetail } from '../types'

export interface SignalFactor {
  label: string
  detail?: string
}

export function getSupportingFactors(signal: SignalDetail): SignalFactor[] {
  const factors: SignalFactor[] = signal.active_signals.map((label) => ({ label }))

  if (signal.indicators.in_uptrend) {
    factors.push({ label: 'Price is in an established uptrend' })
  }
  if (signal.indicators.macd_bias === 'bullish' && !signal.active_signals.some((s) => s.includes('MACD'))) {
    factors.push({ label: 'MACD trending bullish' })
  }
  if (signal.indicators.rsi_zone === 'oversold' && !signal.active_signals.some((s) => s.includes('RSI'))) {
    factors.push({ label: 'RSI recovering from oversold levels' })
  }

  return factors
}

export function getWarningFactors(signal: SignalDetail): SignalFactor[] {
  const factors: SignalFactor[] = []

  if (signal.indicators.rsi_zone === 'overbought') {
    factors.push({ label: 'RSI in overbought territory', detail: 'Momentum may be stretched.' })
  }
  if (signal.indicators.bb_zone === 'above upper band') {
    factors.push({ label: 'Price above upper Bollinger band', detail: 'Historically prone to pull back.' })
  }
  if (signal.indicators.macd_bias === 'bearish') {
    factors.push({ label: 'MACD trending bearish' })
  }
  if (signal.indicators.volume_note === 'low volume') {
    factors.push({ label: 'Low trading volume', detail: 'Signal may be less reliable on thin trading.' })
  }
  if (signal.sell_confidence !== null && signal.sell_confidence >= 0.45) {
    factors.push({
      label: 'Elevated downside risk detected',
      detail: `Sell-risk confidence ${Math.round(signal.sell_confidence * 100)}%.`,
    })
  }

  return factors
}
