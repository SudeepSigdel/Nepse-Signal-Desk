import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { fetchMe, login as apiLogin, signup as apiSignup } from '../lib/api'
import { clearToken, getToken, onTokenChange, setToken } from '../lib/authToken'
import type { AuthUser } from '../types'

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Called by AuthCallbackPage once it has a token from the Google OAuth redirect. */
  applyToken: (token: string) => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await fetchMe()
      setUser(me)
    } catch {
      clearToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
    return onTokenChange(loadUser)
  }, [loadUser])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiLogin(email, password)
    setToken(access_token)
    await loadUser()
  }, [loadUser])

  const signup = useCallback(async (email: string, password: string) => {
    const { access_token } = await apiSignup(email, password)
    setToken(access_token)
    await loadUser()
  }, [loadUser])

  const logout = useCallback(() => {
    clearToken()
    setUser(null)
  }, [])

  const applyToken = useCallback(async (token: string) => {
    setToken(token)
    await loadUser()
  }, [loadUser])

  const value: AuthContextValue = {
    user,
    loading,
    isAuthenticated: user !== null,
    login,
    signup,
    logout,
    applyToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
