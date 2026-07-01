import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { ModelContextPanel } from '../components/stock/ModelContextPanel'
import { PositionHelper } from '../components/stock/PositionHelper'
import { SignalHistoryPanel } from '../components/stock/SignalHistoryPanel'
import { SignalSummaryPanel } from '../components/stock/SignalSummaryPanel'
import { StockChart } from '../components/stock/StockChart'
import { StockHeader } from '../components/stock/StockHeader'
import { ErrorState } from '../components/ui/ErrorState'
import { Skeleton } from '../components/ui/Skeleton'
import { trendFromDelta } from '../components/ui/TrendIndicator'
import { useStocksContext } from '../context/StocksContext'
import { useConfidenceBaseline } from '../hooks/useConfidenceBaseline'
import { useSignal } from '../hooks/useSignal'
import { useStockDetail } from '../hooks/useStockDetail'
import { formatRelativeTime } from '../lib/format'

export function StockResearchPage() {
  const { symbol = '' } = useParams<{ symbol: string }>()
  const upperSymbol = symbol.toUpperCase()
  const { family, stocks } = useStocksContext()
  const baseline = useConfidenceBaseline(stocks)
  const sector = useMemo(() => stocks.find((s) => s.symbol === upperSymbol)?.sector, [stocks, upperSymbol])

  const { detail, loading: detailLoading, error: detailError, refresh: refreshDetail } = useStockDetail(upperSymbol, 180)
  const { signal, error: signalError, lastUpdated, refresh: refreshSignal } = useSignal(upperSymbol, family)

  const trend = useMemo(() => {
    const delta = baseline[upperSymbol] !== undefined && signal ? signal.buy_confidence - baseline[upperSymbol] : null
    return trendFromDelta(delta)
  }, [baseline, upperSymbol, signal])

  if (signalError || detailError) {
    return (
      <div className="mx-auto max-w-5xl p-4 sm:p-6">
        <ErrorState
          message={signalError ?? detailError ?? 'Failed to load stock data'}
          onRetry={() => {
            refreshDetail()
            refreshSignal()
          }}
        />
      </div>
    )
  }

  if (!signal || !detail) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 p-4 sm:p-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5 p-4 sm:p-6">
      <StockHeader symbol={upperSymbol} close={signal.close} verdict={signal.verdict} trend={trend} sector={sector} />

      <p className="-mt-3 text-xs text-zinc-400 dark:text-zinc-500">
        Signal last checked {formatRelativeTime(lastUpdated)} · data as of {signal.date}
      </p>

      <SignalSummaryPanel signal={signal} />

      <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
        <p className="mb-3 text-sm font-medium text-zinc-700 dark:text-zinc-300">Price &amp; indicators</p>
        <StockChart detail={detail} />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <SignalHistoryPanel symbol={upperSymbol} confidence={signal.buy_confidence} verdict={signal.verdict} date={signal.date} />
        <ModelContextPanel signal={signal} />
      </div>

      <PositionHelper symbol={upperSymbol} currentPrice={signal.close} currentBuyConfidence={signal.buy_confidence} />

      {detailLoading && <p className="text-xs text-zinc-400 dark:text-zinc-500">Refreshing chart data…</p>}
    </div>
  )
}
