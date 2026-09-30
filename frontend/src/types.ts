// Shared types mirroring app/schemas.py response shapes.

export type ModelFamily = 'xgboost' | 'random_forest' | 'both'

export type Verdict = 'BUY' | 'MODERATE' | 'SELL' | 'WEAK_SELL' | 'HOLD' | 'AVOID'

export type Tier = 'High' | 'Medium' | 'Low' | 'Weak'

// Coarse grouping used for filters and the action board.
// BUY: verdict BUY/MODERATE. WATCH: HOLD with decent confidence. SELL_RISK: SELL/WEAK_SELL.
export type SignalGroup = 'buy' | 'watch' | 'hold' | 'sell_risk'

export interface Stock {
  symbol: string
  date: string
  close: number | null
  rsi: number | null
  volume_ratio: number | null
  change_pct: number | null
  turnover: number | null
  sector: string | null
  sub_index: string | null
  confidence: number
  buy_confidence: number | null
  rf_confidence: number | null
  sell_confidence: number | null
  verdict: Verdict | null
  tier: Tier
}

export interface StocksListResponse {
  stocks: Stock[]
  count: number
}

export interface CandleData {
  t: string
  o: number | null
  h: number | null
  l: number | null
  c: number | null
  v: number | null
}

export interface IndicatorData {
  sma20: (number | null)[]
  bb_upper: (number | null)[]
  bb_lower: (number | null)[]
  bb_mid: (number | null)[]
  ema12: (number | null)[]
  ema26: (number | null)[]
  rsi: (number | null)[]
  macd: (number | null)[]
  macd_sig: (number | null)[]
  macd_hist: (number | null)[]
  volume: (number | null)[]
  dates: string[]
}

export interface StockDetail {
  symbol: string
  days: number
  candles: CandleData[]
  indicators: IndicatorData
  has_more: boolean
}

export interface SignalIndicators {
  rsi: number | null
  rsi_zone: string
  macd: number | null
  macd_signal: number | null
  macd_hist: number | null
  macd_bias: string
  bb_pctb: number | null
  bb_zone: string
  in_uptrend: boolean
  volume_ratio: number | null
  volume_note: string
}

export interface SignalThresholds {
  buy_high: number
  buy_medium: number
  buy_low: number
}

export interface SignalDetail {
  symbol: string
  date: string
  close: number | null
  buy_confidence: number
  sell_confidence: number | null
  relative_strength: number | null
  relative_strength_note: string | null
  verdict: string
  verdict_color: string
  description: string
  active_signals: string[]
  indicators: SignalIndicators
  thresholds: SignalThresholds
}

export interface SummarySignal {
  symbol: string
  close: number | null
  date: string
  rsi: number | null
  confidence: number
  signals: string[]
  in_uptrend: boolean
}

export interface SummaryResponse {
  top_signals: SummarySignal[]
  total_above_threshold: number
  threshold_used: number
}

export interface FoldMetric {
  fold: number
  test_period: string
  train_rows: number
  test_rows: number
  auc: number
}

export interface CalibrationBucket {
  label: string
  min_confidence: number
  max_confidence: number
  predicted_avg: number | null
  actual_rate: number | null
  count: number
}

export interface ModelSection {
  fold_metrics: FoldMetric[]
  mean_auc: number | null
  calibration: CalibrationBucket[]
}

export interface ThresholdRow {
  threshold: number
  trades: number
  win_rate_pct: number
  profit_factor: number
  mean_return_pct: number
  sharpe: number
}

export interface StrategyRow {
  strategy: string
  trades: number
  win_rate_pct: number
  profit_factor: number
  mean_return_pct: number
  sharpe: number
}

// ─── Auth & persisted user data (backend response shapes) ───

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface AuthUser {
  id: number
  email: string
  has_password: boolean
}

export interface WatchlistItemRecord {
  symbol: string
}

export interface HoldingCreate {
  symbol: string
  entry_date: string
  entry_price: number
  quantity: number | null
}

export interface HoldingRecord {
  id: number
  symbol: string
  entry_date: string
  entry_price: number
  quantity: number | null
  created_at: string
}

export interface ModelPerformanceResponse {
  family: string
  buy: ModelSection
  sell: ModelSection
  thresholds: ThresholdRow[]
  strategy_comparison: StrategyRow[]
}

export type ExitType = 'time_based' | 'stop_loss' | 'signal_decay'

export interface PositionCheckRequest {
  symbol: string
  entry_date: string
  entry_price: number
  current_price: number
  current_buy_conf: number
}

export interface ExitStatusResponse {
  should_exit: boolean
  reason: string | null
  exit_type: ExitType | null
  days_held: number
  days_remaining: number
  current_return_pct: number
  distance_to_stop_loss_pct: number
  risks: string[]
}

// ─── Client-side shapes for persisted (backend) or local-only concepts ───

export interface Holding {
  id: string
  symbol: string
  entryDate: string // ISO date, yyyy-mm-dd
  entryPrice: number
  quantity: number | null
  createdAt: number
}

export interface ConfidenceLogEntry {
  timestamp: number
  date: string
  confidence: number
  verdict: string
}

// ─── Paper trading ─────────────────────────────────────────

export type OrderSide = 'buy' | 'sell'
export type OrderType = 'market' | 'limit'
export type OrderStatus = 'pending' | 'filled' | 'rejected' | 'cancelled' | 'expired'

export interface PaperPosition {
  symbol: string
  qty: number
  avg_cost: number
  last_price: number | null
  price_source: 'live' | 'eod' | null
  market_value: number | null
  unrealized_pnl: number | null
  unrealized_pct: number | null
  first_buy_date: string
}

export interface PaperAccount {
  id: number
  name: string
  is_agent: boolean
  starting_cash: number
  cash: number
  available_cash: number
  equity: number
  unrealized_pnl: number
  realized_pnl: number
  fees_paid: number
  return_pct: number
  positions: PaperPosition[]
  created_at: string
}

export interface FeeBreakdown {
  side: OrderSide
  trade_value: number
  broker_commission: number
  commission_rate: number
  sebon_fee: number
  dp_charge: number
  capital_gains_tax: number
  cgt_rate: number
  realized_gain: number
  total_fees: number
  net_amount: number
}

export interface PaperOrder {
  id: number
  account_id: number
  symbol: string
  side: OrderSide
  order_type: OrderType
  qty: number
  limit_price: number | null
  status: OrderStatus
  reject_reason: string | null
  reserved_cash: number
  created_at: string
  filled_at: string | null
  fill_price: number | null
  price_source: 'live' | 'eod' | null
  fees: FeeBreakdown | null
  realized_pnl: number | null
}

export interface PaperOrderCreate {
  symbol: string
  side: OrderSide
  order_type: OrderType
  qty: number
  limit_price?: number | null
}

export interface PaperEquityPoint {
  date: string
  cash: number
  equity: number
}

export interface Quote {
  symbol: string
  price: number
  prev_close: number | null
  day_high: number | null
  day_low: number | null
  as_of: string
  source: 'live' | 'eod'
  band_reference: number | null
  circuit_low: number | null
  circuit_high: number | null
  market_open: boolean
}

export interface FeePreviewRequest {
  side: OrderSide
  price: number
  qty: number
  avg_cost?: number | null
  holding_days?: number
}

export interface LeaderboardEntry {
  rank: number
  account_id: number
  account_name: string
  trader: string
  is_agent: boolean
  equity: number
  return_pct: number
  trades: number
}
