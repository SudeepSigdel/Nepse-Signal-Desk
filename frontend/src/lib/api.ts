import axios from 'axios'
import { API_BASE_URL } from '../config'
import { getToken } from './authToken'
import type {
  AgentReport,
  AuthUser,
  LiveAgent,
  FeeBreakdown,
  FeePreviewRequest,
  LeaderboardEntry,
  PaperAccount,
  PaperEquityPoint,
  PaperOrder,
  PaperOrderCreate,
  Quote,
  ExitStatusResponse,
  HoldingCreate,
  HoldingRecord,
  ModelPerformanceResponse,
  PositionCheckRequest,
  SignalDetail,
  StockDetail,
  StocksListResponse,
  SummaryResponse,
  TokenResponse,
  WatchlistItemRecord,
} from '../types'

export const api = axios.create({ baseURL: API_BASE_URL })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function fetchStocks(family?: string): Promise<StocksListResponse> {
  const { data } = await api.get<StocksListResponse>('/api/stocks', {
    params: family ? { family } : undefined,
  })
  return data
}

export async function fetchStockDetail(symbol: string, days: number, offset = 0): Promise<StockDetail> {
  const { data } = await api.get<StockDetail>(`/api/stocks/${symbol}`, { params: { days, offset } })
  return data
}

export async function fetchSignal(symbol: string, family?: string): Promise<SignalDetail> {
  const { data } = await api.get<SignalDetail>(`/api/signal/${symbol}`, {
    params: family && family !== 'both' ? { family } : undefined,
  })
  return data
}

export async function fetchSummary(family?: string): Promise<SummaryResponse> {
  const { data } = await api.get<SummaryResponse>('/api/summary', {
    params: family ? { family } : undefined,
  })
  return data
}

export async function checkPositionExit(payload: PositionCheckRequest): Promise<ExitStatusResponse> {
  const { data } = await api.post<ExitStatusResponse>('/api/positions/exit-check', payload)
  return data
}

export async function fetchModelPerformance(family: string): Promise<ModelPerformanceResponse> {
  const { data } = await api.get<ModelPerformanceResponse>('/api/model-performance', { params: { family } })
  return data
}

// ─── Auth ────────────────────────────────────────────────

export async function signup(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/api/auth/signup', { email, password })
  return data
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/api/auth/login', { email, password })
  return data
}

export async function fetchMe(): Promise<AuthUser> {
  const { data } = await api.get<AuthUser>('/api/auth/me')
  return data
}

export function googleLoginUrl(): string {
  return `${API_BASE_URL}/api/auth/google/login`
}

// ─── Watchlist (persisted) ─────────────────────────────────

export async function fetchWatchlist(): Promise<WatchlistItemRecord[]> {
  const { data } = await api.get<WatchlistItemRecord[]>('/api/watchlist')
  return data
}

export async function addWatchlistSymbol(symbol: string): Promise<WatchlistItemRecord[]> {
  const { data } = await api.post<WatchlistItemRecord[]>(`/api/watchlist/${symbol}`)
  return data
}

export async function removeWatchlistSymbol(symbol: string): Promise<WatchlistItemRecord[]> {
  const { data } = await api.delete<WatchlistItemRecord[]>(`/api/watchlist/${symbol}`)
  return data
}

// ─── Holdings (persisted) ──────────────────────────────────

export async function fetchHoldings(): Promise<HoldingRecord[]> {
  const { data } = await api.get<HoldingRecord[]>('/api/holdings')
  return data
}

export async function createHolding(payload: HoldingCreate): Promise<HoldingRecord> {
  const { data } = await api.post<HoldingRecord>('/api/holdings', payload)
  return data
}

export async function deleteHolding(id: number): Promise<void> {
  await api.delete(`/api/holdings/${id}`)
}

// ─── Paper trading ─────────────────────────────────────────

export async function fetchPaperAccounts(): Promise<PaperAccount[]> {
  const { data } = await api.get<PaperAccount[]>('/api/paper/accounts')
  return data
}

export async function createPaperAccount(name: string, startingCash: number): Promise<PaperAccount> {
  const { data } = await api.post<PaperAccount>('/api/paper/accounts', { name, starting_cash: startingCash })
  return data
}

export async function resetPaperAccount(accountId: number): Promise<PaperAccount> {
  const { data } = await api.post<PaperAccount>(`/api/paper/accounts/${accountId}/reset`)
  return data
}

export async function fetchPaperOrders(accountId: number): Promise<PaperOrder[]> {
  const { data } = await api.get<PaperOrder[]>(`/api/paper/accounts/${accountId}/orders`)
  return data
}

export async function placePaperOrder(accountId: number, payload: PaperOrderCreate): Promise<PaperOrder> {
  const { data } = await api.post<PaperOrder>(`/api/paper/accounts/${accountId}/orders`, payload)
  return data
}

export async function cancelPaperOrder(orderId: number): Promise<PaperOrder> {
  const { data } = await api.post<PaperOrder>(`/api/paper/orders/${orderId}/cancel`)
  return data
}

export async function fetchPaperEquity(accountId: number): Promise<PaperEquityPoint[]> {
  const { data } = await api.get<PaperEquityPoint[]>(`/api/paper/accounts/${accountId}/equity`)
  return data
}

export async function fetchQuote(symbol: string): Promise<Quote> {
  const { data } = await api.get<Quote>(`/api/paper/quote/${encodeURIComponent(symbol)}`)
  return data
}

export async function fetchFeePreview(payload: FeePreviewRequest): Promise<FeeBreakdown> {
  const { data } = await api.post<FeeBreakdown>('/api/paper/fee-preview', payload)
  return data
}

export async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  const { data } = await api.get<LeaderboardEntry[]>('/api/paper/leaderboard')
  return data
}

/** Pull FastAPI's `detail` message out of an axios error, for inline form errors. */
export function apiErrorMessage(err: unknown, fallback = 'Request failed'): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  }
  return err instanceof Error ? err.message : fallback
}

// ─── Trading agents ────────────────────────────────────────

export async function fetchAgentReport(family = 'xgboost'): Promise<AgentReport> {
  const { data } = await api.get<AgentReport>('/api/agents/report', { params: { family } })
  return data
}

export async function fetchLiveAgents(): Promise<LiveAgent[]> {
  const { data } = await api.get<LiveAgent[]>('/api/agents/live')
  return data
}
