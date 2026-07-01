import axios from 'axios'
import { API_BASE_URL } from '../config'
import { getToken } from './authToken'
import type {
  AuthUser,
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

export async function fetchStockDetail(symbol: string, days: number): Promise<StockDetail> {
  const { data } = await api.get<StockDetail>(`/api/stocks/${symbol}`, { params: { days } })
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
