/**
 * Glossary Modal - Explains technical indicators in plain language.
 * Click the ? icons throughout the app to learn what things mean.
 */

import React, { useState } from 'react'

export function GlossaryModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'what' | 'how' | 'glossary'>('what')

  const closeModal = () => setIsOpen(false)

  return (
    <>
      <button 
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-12 h-12 rounded-full bg-blue-500 hover:bg-blue-600 text-white font-bold text-lg transition-colors shadow-lg"
        title="Help & Learning"
      >
        ?
      </button>

      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={closeModal}>
          <div 
            className="bg-neutral-900 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto border border-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="sticky top-0 bg-neutral-900 border-b border-white/10 px-6 py-4 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-white">Learning Center</h2>
              <button 
                onClick={closeModal}
                className="text-neutral-400 hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/10 px-6">
              <button
                onClick={() => setActiveTab('what')}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeTab === 'what' 
                    ? 'text-blue-400 border-b-2 border-blue-500' 
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                What is this?
              </button>
              <button
                onClick={() => setActiveTab('how')}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeTab === 'how' 
                    ? 'text-blue-400 border-b-2 border-blue-500' 
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                How to use
              </button>
              <button
                onClick={() => setActiveTab('glossary')}
                className={`px-4 py-3 font-medium transition-colors ${
                  activeTab === 'glossary' 
                    ? 'text-blue-400 border-b-2 border-blue-500' 
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Glossary
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-6 space-y-4">
              {activeTab === 'what' && (
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold text-white">What is NEPSE Signal?</h3>
                  <p className="text-neutral-300">
                    NEPSE Signal uses AI to analyze stock price patterns and predict which stocks are likely to go up. We show you the best buying opportunities and warn you about risky stocks.
                  </p>
                  
                  <h4 className="text-lg font-semibold text-white mt-6">The Color Code</h4>
                  <div className="space-y-2">
                    <div className="flex gap-3">
                      <div className="w-4 h-4 rounded bg-green-500 mt-1"></div>
                      <div>
                        <p className="text-white font-medium">🟢 Green = Strong Buy</p>
                        <p className="text-neutral-400 text-sm">AI is very confident. Good opportunity to buy.</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-4 h-4 rounded bg-amber-500 mt-1"></div>
                      <div>
                        <p className="text-white font-medium">🟠 Orange = Moderate</p>
                        <p className="text-neutral-400 text-sm">AI sees potential but not strong. Wait for better price.</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-4 h-4 rounded bg-gray-500 mt-1"></div>
                      <div>
                        <p className="text-white font-medium">⚪ Gray = Neutral</p>
                        <p className="text-neutral-400 text-sm">No clear signal. Skip this stock.</p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <div className="w-4 h-4 rounded bg-red-500 mt-1"></div>
                      <div>
                        <p className="text-white font-medium">🔴 Red = Avoid</p>
                        <p className="text-neutral-400 text-sm">AI doesn't see a good buy opportunity here. Model thinks this stock may go down. Don't buy right now.</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'how' && (
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold text-white">How to Use NEPSE Signal</h3>
                  
                  <div>
                    <h4 className="text-white font-semibold mb-2">Step 1: Find Good Stocks</h4>
                    <p className="text-neutral-300">Go to the dashboard and look for GREEN or ORANGE signals. These are the best opportunities.</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-2">Step 2: Click to Learn More</h4>
                    <p className="text-neutral-300">Click any stock to see the full analysis: price chart, AI explanation, and what to do next.</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-2">Step 3: Set Your Risks</h4>
                    <p className="text-neutral-300">Before buying, set a STOP-LOSS (price where you'll exit if wrong) and PROFIT TARGET (price where you'll sell if right).</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-2">Step 4: Start Small</h4>
                    <p className="text-neutral-300">Don't put all your money in one stock. Buy a little, see if it works, then buy more.</p>
                  </div>

                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mt-6">
                    <p className="text-red-300 font-semibold">⚠️ Important Disclaimer</p>
                    <p className="text-neutral-300 text-sm mt-2">
                      Past performance does not guarantee future results. This is not financial advice. Do your own research before investing. Only invest money you can afford to lose.
                    </p>
                  </div>
                </div>
              )}

              {activeTab === 'glossary' && (
                <div className="space-y-6">
                  <div>
                    <h4 className="text-white font-semibold mb-1">Confidence Score</h4>
                    <p className="text-neutral-300 text-sm">Percentage showing how sure the AI is. Higher = more confident. 80% = AI got 80% of similar trades right in the past.</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-1">RSI (Momentum)</h4>
                    <p className="text-neutral-300 text-sm">Measures if stock is "too hot" or "too cold":</p>
                    <p className="text-neutral-300 text-sm ml-2">• Below 30 = Oversold (cheap, may bounce up)</p>
                    <p className="text-neutral-300 text-sm ml-2">• Above 70 = Overbought (expensive, may drop)</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-1">MACD (Trend)</h4>
                    <p className="text-neutral-300 text-sm">Shows if more buyers or sellers are active:</p>
                    <p className="text-neutral-300 text-sm ml-2">• Bullish = More buyers coming (price may rise)</p>
                    <p className="text-neutral-300 text-sm ml-2">• Bearish = More sellers coming (price may fall)</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-1">Volume</h4>
                    <p className="text-neutral-300 text-sm">Number of shares traded. High volume = strong move. Low volume = weak move.</p>
                  </div>

                  <div>
                    <h4 className="text-white font-semibold mb-1">Bollinger Bands</h4>
                    <p className="text-neutral-300 text-sm">Shows normal price range. Prices outside the range often bounce back in.</p>
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t border-white/10 px-6 py-4">
              <button
                onClick={closeModal}
                className="w-full bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 rounded-lg transition-colors"
              >
                Got it, close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
