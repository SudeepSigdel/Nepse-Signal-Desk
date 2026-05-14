import DashboardOverview from './components/DashboardOverview'
import StockDetailPage from './components/StockDetailPage'
import './App.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<DashboardOverview />} />
        <Route path="/stocks/:symbol" element={<StockDetailPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
