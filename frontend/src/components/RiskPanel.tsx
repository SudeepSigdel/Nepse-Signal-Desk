/**
 * Risk Panel Component
 * Shows disclaimers, accuracy info, and portfolio tips
 */

import React, { useState } from 'react'

export function RiskPanel() {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <>
      {/* Disclaimer Banner */}
      <div className="glass-panel rounded-xl p-4 border border-red-500/20 bg-red-500/5 mb-6">
        <div className="flex items-start gap-3">
          <div className="text-xl mt-1">⚠️</div>
          <div className="flex-1">
            <p className="font-semibold text-red-300 mb-1">Important Disclaimer</p>
            <p className="text-neutral-300 text-sm leading-relaxed">
              <strong>Past performance does not guarantee future results.</strong> This is not financial advice. 
              Stock prices can fall as well as rise. Only invest money you can afford to lose completely. 
              Consult a licensed financial advisor before making investment decisions.
            </p>
          </div>
        </div>
      </div>

      {/* Accuracy & Info */}
      <div className="glass-panel rounded-xl p-5 mb-6">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between hover:opacity-80 transition-opacity"
        >
          <h3 className="font-semibold text-white">About Our Model</h3>
          <span className="text-neutral-400">{isExpanded ? '−' : '+'}</span>
        </button>

        {isExpanded && (
          <div className="mt-4 space-y-4 pt-4 border-t border-white/10">
            <div>
              <p className="text-sm text-neutral-400 mb-2">Historical Accuracy (10-day prediction):</p>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-neutral-800 rounded-full overflow-hidden">
                  <div className="h-full w-[55%] bg-emerald-500 rounded-full"></div>
                </div>
                <span className="text-emerald-400 font-semibold min-w-fit">~55%</span>
              </div>
              <p className="text-xs text-neutral-500 mt-1">
                Our AI correctly predicts the direction ~55% of the time. Better than 50% (coin flip) but not guaranteed.
              </p>
            </div>

            <div>
              <p className="text-sm text-neutral-400 mb-2">High Confidence Trades (65%+):</p>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-neutral-800 rounded-full overflow-hidden">
                  <div className="h-full w-[62%] bg-emerald-500 rounded-full"></div>
                </div>
                <span className="text-emerald-400 font-semibold min-w-fit">~62%</span>
              </div>
              <p className="text-xs text-neutral-500 mt-1">
                When we show green signals (high confidence), they work out about 62% of the time.
              </p>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 mt-4">
              <p className="text-sm text-blue-300">
                💡 <strong>Tip:</strong> Focus on GREEN signals for best odds. Skip gray/red signals when uncertain.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Portfolio Tips */}
      <div className="glass-panel rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Portfolio Tips for Retail Investors</h3>
        
        <div className="space-y-4">
          <div className="flex gap-3">
            <div className="text-lg flex-shrink-0">💰</div>
            <div>
              <p className="font-medium text-white text-sm">Don't put all eggs in one basket</p>
              <p className="text-neutral-400 text-xs">Spread your money across 5-10 different stocks, not just 1-2</p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="text-lg flex-shrink-0">🛡️</div>
            <div>
              <p className="font-medium text-white text-sm">Always set a stop-loss</p>
              <p className="text-neutral-400 text-xs">Decide before buying: "If this stock drops 10%, I'll sell." Stick to it.</p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="text-lg flex-shrink-0">🎯</div>
            <div>
              <p className="font-medium text-white text-sm">Set profit targets</p>
              <p className="text-neutral-400 text-xs">Decide: "If this stock rises 15%, I'll sell half." Lock in gains.</p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="text-lg flex-shrink-0">📰</div>
            <div>
              <p className="font-medium text-white text-sm">Check company news</p>
              <p className="text-neutral-400 text-xs">Don't invest based on signals alone. Read about the company first.</p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="text-lg flex-shrink-0">⏰</div>
            <div>
              <p className="font-medium text-white text-sm">Be patient</p>
              <p className="text-neutral-400 text-xs">Our signals are for 10-day predictions. Don't expect instant results.</p>
            </div>
          </div>

          <div className="flex gap-3">
            <div className="text-lg flex-shrink-0">❌</div>
            <div>
              <p className="font-medium text-white text-sm">Don't use leverage</p>
              <p className="text-neutral-400 text-xs">Don't borrow money to trade. Losses are magnified with leverage.</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
