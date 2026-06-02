import { useState } from 'react';

export interface ExitStatus {
  should_exit: boolean;
  reason?: string;
  exit_type?: 'time_based' | 'stop_loss' | 'signal_decay';
  days_held: number;
  days_remaining: number;
  current_return_pct: number;
  distance_to_stop_loss_pct: number;
  risks: string[];
}

interface PositionExitGuidanceProps {
  status: ExitStatus;
  onExit?: () => void;
}

/**
 * Displays exit guidance for active positions.
 * Shows days held, return %, stop-loss distance, and active risks.
 * Alerts user if exit is recommended.
 */
export function PositionExitGuidance({ status, onExit }: PositionExitGuidanceProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Exit reason icons are intentionally omitted for a cleaner UI

  const getRiskColor = (risk: string): string => {
    if (risk.includes('Signal')) return 'text-yellow-600 dark:text-yellow-400';
    if (risk.includes('Stop-loss')) return 'text-red-600 dark:text-red-400';
    if (risk.includes('approaching')) return 'text-orange-600 dark:text-orange-400';
    return 'text-slate-700 dark:text-neutral-300';
  };

  // URGENT EXIT NEEDED
  if (status.should_exit) {
    return (
      <div className="bg-red-50 dark:bg-red-500/20 border-2 border-red-500 rounded-lg p-4 space-y-3">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-red-700 dark:text-red-400 font-bold text-lg">
              {status.reason}
            </p>
            <p className="text-red-600 dark:text-red-300 text-sm mt-1">
              Exit type: {status.exit_type?.replace(/_/g, ' ').toUpperCase()}
            </p>
          </div>
          {onExit && (
            <button
              onClick={onExit}
              className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-white text-sm font-semibold transition"
            >
              Exit Now
            </button>
          )}
        </div>

        <div className="bg-red-100/50 dark:bg-red-900/30 rounded p-2 text-red-800 dark:text-red-300 text-xs">
          <p className="font-semibold">Immediate action required</p>
          <p className="mt-1">Your position is triggering an exit signal. Consider exiting soon.</p>
        </div>
      </div>
    );
  }

  // NORMAL POSITION STATUS
  return (
    <div className="bg-blue-50/70 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/30 rounded-lg">
      {/* Header - Collapse Toggle */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between p-4 hover:bg-blue-500/5 transition"
      >
        <h3 className="text-slate-900 dark:text-white font-bold flex items-center gap-2">
          Position Status {isCollapsed ? '▼' : '▲'}
        </h3>
        <span className="text-slate-600 dark:text-neutral-400 text-sm font-semibold">
          {status.days_held}/{10} days
        </span>
      </button>

      {!isCollapsed && (
        <div className="border-t border-blue-100 dark:border-blue-500/20 p-4 space-y-4">
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-4">
            {/* Days Held */}
            <div>
              <p className="text-slate-500 dark:text-neutral-400 text-xs mb-1">Days Held</p>
              <p className="text-slate-900 dark:text-white font-bold text-lg">{status.days_held} / 10</p>
              <div className="w-full bg-slate-200 dark:bg-neutral-700 rounded h-2 mt-2">
                <div
                  className="bg-blue-500 h-2 rounded transition-all"
                  style={{ width: `${(status.days_held / 10) * 100}%` }}
                />
              </div>
              {status.days_remaining <= 2 && status.days_remaining > 0 && (
                <p className="text-orange-600 dark:text-orange-400 text-xs mt-1">Approaching 10-day exit</p>
              )}
            </div>

            {/* Current Return */}
            <div>
              <p className="text-slate-500 dark:text-neutral-400 text-xs mb-1">Current Return</p>
              <p
                className={`font-bold text-lg ${
                  status.current_return_pct > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
                }`}
              >
                {status.current_return_pct > 0 ? '+' : ''}{status.current_return_pct.toFixed(2)}%
              </p>
            </div>

            {/* Stop-Loss Distance */}
            <div>
              <p className="text-slate-500 dark:text-neutral-400 text-xs mb-1">Stop-loss Distance</p>
              <p className="text-slate-900 dark:text-white font-bold text-lg">
                {status.distance_to_stop_loss_pct.toFixed(1)}%
              </p>
              {status.distance_to_stop_loss_pct < 1.5 && (
                <p className="text-red-600 dark:text-red-400 text-xs mt-1">Close to stop-loss</p>
              )}
            </div>

            {/* Days Remaining */}
            <div>
              <p className="text-slate-500 dark:text-neutral-400 text-xs mb-1">Days Remaining</p>
              <p className="text-slate-900 dark:text-white font-bold text-lg">{status.days_remaining}</p>
              {status.days_remaining <= 1 && (
                <p className="text-red-600 dark:text-red-400 text-xs mt-1 font-semibold">Final day!</p>
              )}
            </div>
          </div>

          {/* Active Risks Section */}
          {status.risks.length > 0 && (
            <div className="bg-slate-100 dark:bg-neutral-900/50 rounded p-3 border border-black/5 dark:border-transparent">
              <p className="text-yellow-700 dark:text-yellow-400 text-xs font-semibold mb-2">Active Risks:</p>
              <div className="space-y-1">
                {status.risks.map((risk, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <span className="text-slate-400 dark:text-neutral-500 text-xs mt-0.5">•</span>
                    <p className={`text-xs ${getRiskColor(risk)}`}>{risk}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Risks */}
          {status.risks.length === 0 && (
            <div className="bg-emerald-50 dark:bg-green-900/20 border border-emerald-200 dark:border-green-500/30 rounded p-3">
              <p className="text-emerald-700 dark:text-green-400 text-xs font-semibold">Position looks good</p>
              <p className="text-emerald-600 dark:text-green-300/70 text-xs mt-1 font-medium">
                No immediate exit risks. Continue monitoring.
              </p>
            </div>
          )}

          {/* Guidance Box */}
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-500/30 rounded p-3">
            <p className="text-blue-700 dark:text-blue-400 text-xs font-semibold mb-1">Exit Guidance</p>
            <p className="text-blue-600/90 dark:text-blue-300/80 text-xs">
              Your position will automatically exit after 10 days, or if stop-loss (-5%) is hit.
              Monitor daily confidence score for early exit signals.
            </p>
          </div>

          {/* Exit Button */}
          {onExit && (
            <button
              onClick={onExit}
              className="w-full bg-slate-200 hover:bg-slate-300 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-slate-800 dark:text-neutral-200 py-2 rounded text-sm font-medium transition"
            >
              Exit Position
            </button>
          )}
        </div>
      )}
    </div>
  );
}
