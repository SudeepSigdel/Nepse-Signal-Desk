import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { AppShell } from './components/layout/AppShell'
import { AuthProvider } from './context/AuthContext'
import { StocksProvider } from './context/StocksContext'
import { UserDataProvider } from './context/UserDataContext'
import { DashboardPage } from './pages/DashboardPage'

// Lazy-loaded: keeps the initial bundle focused on the landing page rather
// than bundling every page's dependencies (lightweight-charts, chart.js)
// into one ~650kB chunk loaded on first paint.
const LoginPage = lazy(() => import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const SignupPage = lazy(() => import('./pages/SignupPage').then((m) => ({ default: m.SignupPage })))
const AuthCallbackPage = lazy(() => import('./pages/AuthCallbackPage').then((m) => ({ default: m.AuthCallbackPage })))
const MarketsPage = lazy(() => import('./pages/MarketsPage').then((m) => ({ default: m.MarketsPage })))
const StockResearchPage = lazy(() => import('./pages/StockResearchPage').then((m) => ({ default: m.StockResearchPage })))
const WatchlistPage = lazy(() => import('./pages/WatchlistPage').then((m) => ({ default: m.WatchlistPage })))
const PortfolioPage = lazy(() => import('./pages/PortfolioPage').then((m) => ({ default: m.PortfolioPage })))
const TrustPage = lazy(() => import('./pages/TrustPage').then((m) => ({ default: m.TrustPage })))

function PageFallback() {
  return <p className="p-6 text-sm text-zinc-400 dark:text-zinc-500">Loading…</p>
}

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <UserDataProvider>
          <StocksProvider>
            <Suspense fallback={<PageFallback />}>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/auth/callback" element={<AuthCallbackPage />} />
                <Route element={<AppShell />}>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/markets" element={<MarketsPage />} />
                  <Route path="/stocks/:symbol" element={<StockResearchPage />} />
                  <Route
                    path="/watchlist"
                    element={
                      <ProtectedRoute>
                        <WatchlistPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/portfolio"
                    element={
                      <ProtectedRoute>
                        <PortfolioPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="/trust" element={<TrustPage />} />
                </Route>
              </Routes>
            </Suspense>
          </StocksProvider>
        </UserDataProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
