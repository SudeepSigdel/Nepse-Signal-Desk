"""
Shared configuration constants for backend and frontend.
These define the model's confidence thresholds and signal interpretation.
"""

# ═════════════════════════════════════════════════════════════════════════════
# CONFIDENCE THRESHOLDS
# ═════════════════════════════════════════════════════════════════════════════
# The model outputs a probability (0-1) that a stock is a GOOD BUY OPPORTUNITY.
# These thresholds translate that probability into actionable signal tiers.
#
# IMPORTANT: Use these consistently everywhere (backend, frontend, evaluation, etc.)
# ─────────────────────────────────────────────────────────────────────────────

THRESHOLD_HIGH = 0.65      # Strong buy signal: Good probability of positive return
THRESHOLD_MEDIUM = 0.55    # Moderate buy signal: Some opportunity but not strong
THRESHOLD_LOW = 0.45       # Weak signal: Low probability of success
THRESHOLD_MIN = 0.45       # Minimum threshold; below this = "Avoid"

# ─────────────────────────────────────────────────────────────────────────────
# SIGNAL TIER DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

SIGNAL_TIERS = {
    "High": {
        "min_confidence": THRESHOLD_HIGH,
        "label": "🟢 Strong Buy",
        "action": "Consider buying",
        "description": "High confidence in buy opportunity"
    },
    "Medium": {
        "min_confidence": THRESHOLD_MEDIUM,
        "label": "🟠 Moderate Buy",
        "action": "Wait for better entry or confirmation",
        "description": "Moderate buy potential"
    },
    "Low": {
        "min_confidence": THRESHOLD_LOW,
        "label": "⚪ Weak Signal",
        "action": "Skip this stock",
        "description": "Low confidence, uncertain"
    },
    "Weak": {
        "min_confidence": 0.0,
        "label": "🔴 Avoid",
        "action": "Don't buy right now",
        "description": "Not a good buy opportunity currently"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
# MODEL ACCURACY (for transparency to users)
# ─────────────────────────────────────────────────────────────────────────────

MODEL_STATS = {
    "overall_accuracy": 0.55,           # ~55% of all signals correct
    "high_confidence_accuracy": 0.62,   # ~62% when confidence >= 0.65
    "medium_confidence_accuracy": 0.52, # ~52% when confidence 0.55-0.65
    "lookback_days": 10,                # Signals predict 10-day returns
    "total_trades_backtested": 1200,    # Number of historical trades tested
}

# ─────────────────────────────────────────────────────────────────────────────
# API SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_DAYS_LOOKBACK = 180        # Default chart period
MAX_DAYS_LOOKBACK = 2000           # Maximum days to request
API_REFRESH_INTERVAL_MS = 30000    # Frontend refresh interval (30 seconds)
