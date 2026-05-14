import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import type React from 'react'
import type { StockDetail } from '../hooks/useStocks'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler
)

interface StockChartProps {
  detail: StockDetail
}

export default function StockChart({ detail }: StockChartProps) {
  const labels = detail.indicators.dates
  const candles = detail.candles.filter(
    (candle) => candle.o !== null && candle.h !== null && candle.l !== null && candle.c !== null
  )

  const rsiData = {
    labels,
    datasets: [
      {
        label: 'RSI 14',
        data: detail.indicators.rsi,
        borderColor: '#60a5fa',
        backgroundColor: 'rgba(96, 165, 250, 0.1)',
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
        fill: true,
      },
    ],
  }

  const macdData = {
    labels,
    datasets: [
      {
        label: 'MACD',
        data: detail.indicators.macd,
        borderColor: '#3b82f6',
        backgroundColor: 'transparent',
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
      },
      {
        label: 'Signal',
        data: detail.indicators.macd_sig,
        borderColor: '#8b5cf6',
        backgroundColor: 'transparent',
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 1.5,
        borderDash: [4, 4],
      },
    ],
  }

  const volumeData = {
    labels,
    datasets: [
      {
        label: 'Volume',
        data: detail.indicators.volume,
        backgroundColor: 'rgba(255, 255, 255, 0.1)',
        hoverBackgroundColor: 'rgba(255, 255, 255, 0.2)',
        borderRadius: 2,
      },
    ],
  }

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        labels: { 
          color: '#a3a3a3',
          usePointStyle: true,
          boxWidth: 6,
          font: {
            family: "'Inter', sans-serif",
            size: 11
          }
        },
      },
      tooltip: {
        backgroundColor: 'rgba(10, 10, 10, 0.9)',
        titleColor: '#ffffff',
        bodyColor: '#e5e5e5',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        titleFont: { family: "'Inter', sans-serif", size: 12 },
        bodyFont: { family: "'Inter', sans-serif", size: 12 },
      }
    },
    scales: {
      x: {
        ticks: { color: '#737373', maxRotation: 0, autoSkip: true, maxTicksLimit: 8 },
        grid: { color: 'rgba(255, 255, 255, 0.03)' },
        border: { display: false }
      },
      y: {
        ticks: { color: '#737373', font: { family: "'Space Grotesk', sans-serif" } },
        grid: { color: 'rgba(255, 255, 255, 0.03)' },
        border: { display: false }
      },
    },
  }

  return (
    <div className="grid gap-6">
      <ChartPanel title="Price Action">
        <CandlestickChart candles={candles} labels={labels} />
      </ChartPanel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartPanel title="Momentum (RSI)">
          <Line data={rsiData} options={commonOptions} />
        </ChartPanel>

        <ChartPanel title="Trend (MACD)">
          <Line data={macdData} options={commonOptions} />
        </ChartPanel>
      </div>

      <ChartPanel title="Volume">
        <Bar data={volumeData} options={commonOptions} />
      </ChartPanel>
    </div>
  )
}

function CandlestickChart({
  candles,
  labels,
}: {
  candles: NonNullable<StockDetail['candles'][number]>[]
  labels: string[]
}) {
  const width = 1000
  const height = 320
  const paddingX = 40
  const paddingY = 20

  const values = candles.flatMap((candle) => [candle.o!, candle.h!, candle.l!, candle.c!])
  const minValue = Math.min(...values)
  const maxValue = Math.max(...values)
  const range = Math.max(maxValue - minValue, 1)

  // Add 5% padding to top and bottom of the chart area
  const paddedMin = minValue - (range * 0.05)
  const paddedMax = maxValue + (range * 0.05)
  const paddedRange = paddedMax - paddedMin

  const scaleY = (value: number) =>
    height - paddingY - ((value - paddedMin) / paddedRange) * (height - paddingY * 2)

  const step = (width - paddingX * 2) / Math.max(candles.length, 1)
  const barWidth = Math.max(Math.min(step * 0.6, 8), 2)

  return (
    <div className="h-full w-full overflow-hidden rounded-lg bg-transparent">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-full w-full preserve-3d">
        
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((fraction) => {
          const y = paddingY + fraction * (height - paddingY * 2)
          return (
            <g key={fraction}>
              <line x1={paddingX} x2={width - paddingX} y1={y} y2={y} stroke="rgba(255,255,255,0.03)" strokeDasharray="4 4" />
            </g>
          )
        })}

        {/* Candlesticks */}
        {candles.map((candle, index) => {
          const x = paddingX + index * step + step / 2
          const openY = scaleY(candle.o!)
          const highY = scaleY(candle.h!)
          const lowY = scaleY(candle.l!)
          const closeY = scaleY(candle.c!)
          
          const isBullish = candle.c! >= candle.o!
          const bodyTop = Math.min(openY, closeY)
          const bodyHeight = Math.max(Math.abs(closeY - openY), 1)
          
          // Professional color palette for candles
          const color = isBullish ? '#10b981' : '#ef4444'

          return (
            <g key={`${candle.t}-${index}`} className="transition-opacity hover:opacity-80">
              <line 
                x1={x} x2={x} 
                y1={highY} y2={lowY} 
                stroke={color} 
                strokeWidth="1.5" 
                opacity="0.8"
              />
              <rect
                x={x - barWidth / 2}
                y={bodyTop}
                width={barWidth}
                height={bodyHeight}
                rx="1"
                fill={color}
              />
            </g>
          )
        })}

        {/* X-axis labels (first, middle, last) */}
        {labels.length > 0 && (
          <>
            <text x={paddingX} y={height - 2} fill="#737373" fontSize="11" fontFamily="Inter">
              {labels[0]}
            </text>
            {labels.length > 2 && (
              <text x={width / 2} y={height - 2} fill="#737373" fontSize="11" fontFamily="Inter" textAnchor="middle">
                {labels[Math.floor(labels.length / 2)]}
              </text>
            )}
            <text x={width - paddingX} y={height - 2} fill="#737373" fontSize="11" fontFamily="Inter" textAnchor="end">
              {labels[labels.length - 1]}
            </text>
          </>
        )}
      </svg>
    </div>
  )
}

function ChartPanel({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="glass-panel rounded-xl overflow-hidden flex flex-col">
      <div className="border-b border-white/5 bg-black/20 px-5 py-3">
        <h3 className="text-sm font-semibold text-neutral-200">{title}</h3>
      </div>
      <div className="h-[300px] p-5 bg-black/10">
        {children}
      </div>
    </section>
  )
}
