/**
 * Reusable Signal Card Component
 * Shows 5-level verdict (BUY/MODERATE/SELL/WEAK_SELL/HOLD) with dual confidence scores
 */

interface SignalCardProps {
  verdict_color: string
  buy_confidence: number
  sell_confidence?: number | null
  description: string
  active_signals: string[]
  close?: number
}

export function SignalCard({ 
  verdict_color, 
  buy_confidence,
  sell_confidence,
  description, 
  active_signals,
  close 
}: SignalCardProps) {
  
  // Map colors to emojis and text for 5-level system
  const getSignalVisuals = () => {
    switch (verdict_color) {
      case 'green':
        return {
          emoji: '🟢',
          actionText: 'STRONG BUY — Consider Entering',
          bgClass: 'bg-green-500/10 border-green-500/30',
          textClass: 'text-green-400',
          riskText: 'Low to Medium Risk',
          confidenceLabel: 'Buy Confidence'
        }
      case 'amber':
      case 'orange':
        return {
          emoji: '🟠',
          actionText: 'MODERATE BUY — Wait for Better Entry',
          bgClass: 'bg-amber-500/10 border-amber-500/30',
          textClass: 'text-amber-400',
          riskText: 'Medium Risk',
          confidenceLabel: 'Buy Confidence'
        }
      case 'gray':
        return {
          emoji: '⚪',
          actionText: 'HOLD — No Clear Signal',
          bgClass: 'bg-neutral-500/10 border-neutral-500/30',
          textClass: 'text-neutral-400',
          riskText: 'High Uncertainty',
          confidenceLabel: 'Confidence'
        }
      case 'yellow':
        return {
          emoji: '🟡',
          actionText: 'WEAK SELL — Some Downside Risk',
          bgClass: 'bg-yellow-500/10 border-yellow-500/30',
          textClass: 'text-yellow-400',
          riskText: 'Medium-High Risk',
          confidenceLabel: 'Sell Confidence'
        }
      case 'red':
        return {
          emoji: '🔴',
          actionText: 'SELL — High Downside Risk',
          bgClass: 'bg-red-500/10 border-red-500/30',
          textClass: 'text-red-400',
          riskText: 'High Downside Risk',
          confidenceLabel: 'Sell Confidence'
        }
      default:
        return {
          emoji: '❓',
          actionText: 'UNKNOWN',
          bgClass: 'bg-gray-500/10 border-gray-500/30',
          textClass: 'text-gray-400',
          riskText: 'Unknown Risk',
          confidenceLabel: 'Confidence'
        }
    }
  }

  const visuals = getSignalVisuals()

  // Get action steps based on signal
  const getActionSteps = () => {
    switch (verdict_color) {
      case 'green':
        return [
          "Check recent company news",
          "Set stop-loss 5-10% below",
          "Start with small position"
        ]
      case 'amber':
      case 'orange':
        return [
          "Watch for price dip",
          "Monitor volume increase",
          "Consider buying at -5%"
        ]
      case 'gray':
        return [
          "Look for other stocks",
          "Consider taking profits if holding",
          "Set price alert"
        ]
      case 'yellow':
        return [
          "Risky to buy now",
          "If holding, consider taking profits",
          "Wait for more bullish signals"
        ]
      case 'red':
        return [
          "Don't buy right now",
          "If holding, consider selling",
          "Watch for trend reversal"
        ]
      default:
        return []
    }
  }

  // Get color for confidence bar based on confidence level
  const getConfidenceBarColor = (isSell: boolean) => {
    if (isSell) {
      return verdict_color === 'red' ? 'bg-red-500' :
             verdict_color === 'yellow' ? 'bg-yellow-500' :
             'bg-neutral-500'
    } else {
      return verdict_color === 'green' ? 'bg-green-500' :
             verdict_color === 'amber' || verdict_color === 'orange' ? 'bg-amber-500' :
             'bg-neutral-500'
    }
  }

  const primaryConfidence = verdict_color === 'red' || verdict_color === 'yellow' 
    ? sell_confidence 
    : buy_confidence

  return (
    <div className={`glass-panel rounded-xl p-6 border ${visuals.bgClass}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className="text-3xl">{visuals.emoji}</span>
            <h3 className={`text-2xl font-bold ${visuals.textClass}`}>
              {visuals.actionText}
            </h3>
          </div>
          <p className="text-neutral-400 text-sm">{visuals.riskText}</p>
        </div>
        
        {close && (
          <div className="text-right">
            <p className="text-2xl font-semibold text-white">Rs. {close.toFixed(2)}</p>
            <p className="text-xs text-neutral-500">Current Price</p>
          </div>
        )}
      </div>

      {/* Confidence Bars - Primary */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-neutral-300">{visuals.confidenceLabel}</span>
          <span className={`text-lg font-bold ${visuals.textClass}`}>
            {(primaryConfidence! * 100).toFixed(1)}%
          </span>
        </div>
        <div className="w-full h-2 bg-neutral-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${getConfidenceBarColor(verdict_color === 'red' || verdict_color === 'yellow')}`}
            style={{ width: `${primaryConfidence! * 100}%` }}
          />
        </div>
        <p className="text-xs text-neutral-500 mt-1">
          {primaryConfidence! >= 0.75 ? 'Very high confidence' :
           primaryConfidence! >= 0.65 ? 'High confidence' :
           primaryConfidence! >= 0.55 ? 'Moderate confidence' :
           primaryConfidence! >= 0.45 ? 'Low confidence' :
           'Very low confidence'}
        </p>
      </div>

      {/* Confidence Bars - Secondary (show both when available) */}
      {sell_confidence !== null && sell_confidence !== undefined && 
       verdict_color !== 'red' && verdict_color !== 'yellow' && (
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-neutral-300">Sell Confidence</span>
            <span className="text-lg font-bold text-red-400">
              {(sell_confidence * 100).toFixed(1)}%
            </span>
          </div>
          <div className="w-full h-2 bg-neutral-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all bg-red-500"
              style={{ width: `${sell_confidence * 100}%` }}
            />
          </div>
          <p className="text-xs text-neutral-500 mt-1">
            {sell_confidence >= 0.65 ? 'High downside risk' :
             sell_confidence >= 0.55 ? 'Moderate downside risk' :
             'Low downside risk'}
          </p>
        </div>
      )}

      {/* Description */}
      <div className="bg-black/20 rounded-lg p-4 mb-6 border border-white/5">
        <p className="text-neutral-200 leading-relaxed">
          {description}
        </p>
      </div>

      {/* Active Signals */}
      {active_signals.length > 0 && (
        <div className="mb-6">
          <p className="text-sm font-semibold text-neutral-300 mb-2">Why this signal?</p>
          <div className="flex flex-wrap gap-2">
            {active_signals.map((signal) => (
              <span 
                key={signal}
                className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30"
              >
                ✓ {signal}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Next Steps */}
      <div>
        <p className="text-sm font-semibold text-neutral-300 mb-3">What to do next:</p>
        <div className="space-y-2">
          {getActionSteps().map((step, idx) => (
            <div key={idx} className="flex gap-3">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                verdict_color === 'green' ? 'bg-green-500/20 text-green-400' :
                verdict_color === 'amber' || verdict_color === 'orange' ? 'bg-amber-500/20 text-amber-400' :
                verdict_color === 'gray' ? 'bg-neutral-500/20 text-neutral-400' :
                verdict_color === 'yellow' ? 'bg-yellow-500/20 text-yellow-400' :
                'bg-red-500/20 text-red-400'
              }`}>
                {idx + 1}
              </div>
              <p className="text-neutral-300 text-sm pt-1">{step}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
