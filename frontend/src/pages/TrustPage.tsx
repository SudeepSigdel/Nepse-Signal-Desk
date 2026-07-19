import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { Bar, Chart } from 'react-chartjs-2'
import { useModelPerformance } from '../hooks/useModelPerformance'
import { useTheme } from '../hooks/useTheme'
import '../lib/chartRegistry'
import { baseChartOptions, CHART_COLORS } from '../lib/chartTheme'
import type { ModelSection, StrategyRow, ThresholdRow } from '../types'

const FAMILIES: Array<{ value: 'xgboost' | 'random_forest'; label: string }> = [
  { value: 'random_forest', label: 'Random Forest' },
  { value: 'xgboost', label: 'XGBoost' },
]

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <p className="text-xs text-zinc-500 dark:text-zinc-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">{value}</p>
      <p className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">{detail}</p>
    </div>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">{title}</h2>
      <div className="mt-2 space-y-2 text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">{children}</div>
    </section>
  )
}

function FoldChart({ buy, sell }: { buy: ModelSection; sell: ModelSection }) {
  const { isDark } = useTheme()
  const labels = buy.fold_metrics.map((f) => `Fold ${f.fold}`)

  const data = {
    labels,
    datasets: [
      {
        type: 'bar' as const,
        label: 'BUY model AUC',
        data: buy.fold_metrics.map((f) => f.auc),
        backgroundColor: CHART_COLORS.sma,
        borderWidth: 0,
      },
      {
        type: 'bar' as const,
        label: 'SELL model AUC',
        data: sell.fold_metrics.map((f) => f.auc),
        backgroundColor: CHART_COLORS.macdSignal,
        borderWidth: 0,
      },
      {
        type: 'line' as const,
        label: 'No-skill baseline (0.5)',
        data: labels.map(() => 0.5),
        borderColor: CHART_COLORS.rsiZone,
        borderDash: [4, 4],
        borderWidth: 1,
        pointRadius: 0,
      },
    ],
  }

  const options = {
    ...baseChartOptions(isDark, { min: 0.3, max: 0.65 }),
    plugins: { ...baseChartOptions(isDark).plugins, legend: { display: true, labels: { boxWidth: 10, font: { size: 10 } } } },
  }

  return (
    <div className="h-56">
      <Chart type="bar" data={data} options={options} />
    </div>
  )
}

function CalibrationChart({ section }: { section: ModelSection }) {
  const { isDark } = useTheme()
  const labels = section.calibration.map((b) => b.label)

  const data = {
    labels,
    datasets: [
      {
        label: 'Model-predicted probability',
        data: section.calibration.map((b) => (b.predicted_avg ?? 0) * 100),
        backgroundColor: CHART_COLORS.bb,
        borderWidth: 0,
      },
      {
        label: 'Actual outcome rate',
        data: section.calibration.map((b) => (b.actual_rate ?? 0) * 100),
        backgroundColor: CHART_COLORS.sma,
        borderWidth: 0,
      },
    ],
  }

  const options = {
    ...baseChartOptions(isDark, { min: 0, max: 80 }),
    plugins: { ...baseChartOptions(isDark).plugins, legend: { display: true, labels: { boxWidth: 10, font: { size: 10 } } } },
  }

  return (
    <div>
      <div className="h-48">
        <Bar data={data} options={options} />
      </div>
      <div className="mt-2 grid grid-cols-2 gap-1 text-[11px] text-zinc-400 dark:text-zinc-500 sm:grid-cols-4">
        {section.calibration.map((b) => (
          <span key={b.label}>{b.label}: {b.count.toLocaleString()} samples</span>
        ))}
      </div>
    </div>
  )
}

function StrategyTable({ rows }: { rows: StrategyRow[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
            <th className="px-3 py-2 text-left font-medium">Strategy</th>
            <th className="px-3 py-2 text-right font-medium">Trades</th>
            <th className="px-3 py-2 text-right font-medium">Win rate</th>
            <th className="px-3 py-2 text-right font-medium">Profit factor</th>
            <th className="px-3 py-2 text-right font-medium">Mean return</th>
            <th className="px-3 py-2 text-right font-medium">Sharpe</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
          {rows.map((row) => (
            <tr key={row.strategy}>
              <td className="px-3 py-2 font-medium text-zinc-900 dark:text-zinc-100">{row.strategy}</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-600 dark:text-zinc-400">{row.trades.toLocaleString()}</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.win_rate_pct.toFixed(1)}%</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.profit_factor.toFixed(2)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.mean_return_pct.toFixed(2)}%</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.sharpe.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ThresholdTable({ rows }: { rows: ThresholdRow[] }) {
  return (
    <div className="overflow-hidden rounded-md border border-zinc-200 dark:border-zinc-800">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400">
            <th className="px-3 py-2 text-left font-medium">Confidence threshold</th>
            <th className="px-3 py-2 text-right font-medium">Trades</th>
            <th className="px-3 py-2 text-right font-medium">Win rate</th>
            <th className="px-3 py-2 text-right font-medium">Profit factor</th>
            <th className="px-3 py-2 text-right font-medium">Sharpe</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/70">
          {rows.map((row) => (
            <tr key={row.threshold}>
              <td className="px-3 py-2 font-medium text-zinc-900 dark:text-zinc-100">≥ {(row.threshold * 100).toFixed(0)}%</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-600 dark:text-zinc-400">{row.trades.toLocaleString()}</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.win_rate_pct.toFixed(1)}%</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.profit_factor.toFixed(2)}</td>
              <td className="px-3 py-2 text-right tabular-nums text-zinc-700 dark:text-zinc-300">{row.sharpe.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function TrustPage() {
  const [family, setFamily] = useState<'xgboost' | 'random_forest'>('random_forest')
  const { performance, loading, error } = useModelPerformance(family)

  const backtestedTrades = useMemo(
    () => (performance ? Math.max(...performance.thresholds.map((t) => t.trades), 0) : 0),
    [performance]
  )
  const bestThreshold = useMemo(
    () => (performance ? performance.thresholds[performance.thresholds.length - 1] : null),
    [performance]
  )

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Model trust</h1>
          <p className="mt-0.5 text-sm text-zinc-500 dark:text-zinc-400">
            What the model does, how it was validated, and where it falls short.
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-0.5 rounded-md border border-zinc-200 bg-zinc-50 p-0.5 dark:border-zinc-800 dark:bg-zinc-900">
          {FAMILIES.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setFamily(opt.value)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                family === opt.value
                  ? 'bg-white text-zinc-900 shadow-sm dark:bg-zinc-700 dark:text-zinc-50'
                  : 'text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <Section title="What the model predicts">
        <p>
          For each NEPSE-listed stock, the model estimates two independent probabilities: the chance the stock rises
          more than 1% over the next 10 trading days ("buy confidence"), and the chance it falls more than 1% over
          the same window ("sell confidence"). It does not predict an exact price or a specific date.
        </p>
      </Section>

      <Section title="What data it uses">
        <p>
          Inputs are primarily derived from historical price and volume: moving averages, RSI, MACD, Bollinger Bands,
          volume ratios, and short-term trend/volatility features. When news coverage is available, the pipeline also
          adds a market-wide FinBERT sentiment score and an availability flag. It does not use company fundamentals
          or macroeconomic indicators, and the sentiment input is not company-specific.
        </p>
      </Section>

      <Section title="Relative strength and model refreshes">
        <p>
          Relative strength is a separate XGBoost model estimating whether a stock will outperform the average NEPSE
          stock over the next 10 trading days. It is context, not a prediction that the stock will make a profit, and
          it remains the same when you switch the BUY/SELL model family.
        </p>
        <p>
          XGBoost BUY/SELL and relative-strength models refresh daily after market close. Random Forest refreshes
          weekly on Sunday night, so the two model families may be based on different refresh dates.
        </p>
      </Section>

      <Section title="How it was validated">
        <p>
          The model is evaluated with walk-forward validation across 9 rolling annual folds (2018 through the most
          recent partial year): it is trained on everything up to a cutoff date and tested only on the period
          immediately after, then the window rolls forward and repeats. This avoids testing on data the model could
          have indirectly learned from, which is a common way backtests overstate real-world performance.
        </p>
      </Section>

      {loading && !performance && (
        <p className="text-sm text-zinc-400 dark:text-zinc-500">Loading validation results…</p>
      )}
      {error && <p className="text-sm text-rose-500">Failed to load model performance: {error}</p>}

      {performance && (
        <>
          <div>
            <h2 className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">Walk-forward validation</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <MetricCard
                label="Mean AUC (BUY)"
                value={performance.buy.mean_auc !== null ? performance.buy.mean_auc.toFixed(3) : '—'}
                detail="Across all 9 folds. 0.5 = no better than chance."
              />
              <MetricCard
                label="Mean AUC (SELL)"
                value={performance.sell.mean_auc !== null ? performance.sell.mean_auc.toFixed(3) : '—'}
                detail="Across all 9 folds. 0.5 = no better than chance."
              />
              <MetricCard
                label="Win rate at highest threshold"
                value={bestThreshold ? `${bestThreshold.win_rate_pct.toFixed(1)}%` : '—'}
                detail={bestThreshold ? `When buy confidence ≥ ${(bestThreshold.threshold * 100).toFixed(0)}%` : ''}
              />
              <MetricCard
                label="Backtested trades"
                value={backtestedTrades.toLocaleString()}
                detail="Simulated ML-validated trades across all folds"
              />
            </div>
            <p className="mt-3 mb-1.5 text-xs font-medium text-zinc-600 dark:text-zinc-400">AUC per fold</p>
            <FoldChart buy={performance.buy} sell={performance.sell} />
            <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">
              AUC (area under the ROC curve) measures how well the model ranks eventual winners above losers in each
              test period; 0.5 is random guessing. Performance varies fold to fold — some periods are close to
              chance, none are dramatically better.
            </p>
          </div>

          <div>
            <h2 className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
              Calibration — does confidence mean what it says? (BUY model)
            </h2>
            <CalibrationChart section={performance.buy} />
            <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">
              For stocks the model called "High confidence", how often did the 10-day rise actually happen? If the
              bars are close, the model's stated confidence roughly tracks reality; if the actual rate consistently
              undershoots the predicted rate, treat the stated percentage as optimistic.
            </p>
          </div>

          <div>
            <h2 className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">
              Does the model add value over simpler baselines?
            </h2>
            <StrategyTable rows={performance.strategy_comparison} />
            <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-500">
              "Signal-only" trades every technical setup with no ML filter; "Always-in" holds every stock every day.
              "ML-validated" only trades when the model's confidence clears the threshold used elsewhere in the app.
            </p>
          </div>

          <div>
            <h2 className="mb-2 text-sm font-semibold text-zinc-800 dark:text-zinc-200">Sensitivity to confidence threshold</h2>
            <ThresholdTable rows={performance.thresholds} />
          </div>
        </>
      )}

      <Section title="Disclaimer">
        <ul className="list-disc space-y-1.5 pl-4">
          <li>NEPSE Signal Desk is a research and decision-support tool. It is not financial advice.</li>
          <li>Past performance, including all figures above, does not guarantee future results.</li>
          <li>Always use position sizing, stop-losses, and your own judgment before acting on any signal.</li>
          <li>This is a final-year academic project, not a licensed investment product.</li>
        </ul>
      </Section>
    </div>
  )
}
