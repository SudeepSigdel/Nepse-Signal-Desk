"""
Pydantic schemas for API requests and responses.
Centralized data validation and documentation.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ══════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ══════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    environment: str
    model_loaded: bool
    features_loaded: bool
    symbols_count: int


# ══════════════════════════════════════════════════════════════════
# STOCKS
# ══════════════════════════════════════════════════════════════════

class StockData(BaseModel):
    """Individual stock data in listings."""
    symbol: str
    date: str
    close: Optional[float]
    rsi: Optional[float]
    confidence: float
    tier: str  # High, Medium, Neutral, Low


class StocksListResponse(BaseModel):
    """Response for GET /api/stocks."""
    stocks: List[StockData]
    count: int


class CandleData(BaseModel):
    """OHLCV candlestick data."""
    t: str  # date
    o: Optional[float]  # open
    h: Optional[float]  # high
    l: Optional[float]  # low
    c: Optional[float]  # close
    v: Optional[float]  # volume


class IndicatorData(BaseModel):
    """Technical indicators for a stock."""
    sma20: List[Optional[float]]
    bb_upper: List[Optional[float]]
    bb_lower: List[Optional[float]]
    bb_mid: List[Optional[float]]
    ema12: List[Optional[float]]
    ema26: List[Optional[float]]
    rsi: List[Optional[float]]
    macd: List[Optional[float]]
    macd_sig: List[Optional[float]]
    macd_hist: List[Optional[float]]
    volume: List[Optional[float]]
    dates: List[str]


class StockDetailResponse(BaseModel):
    """Response for GET /api/stocks/{symbol}."""
    symbol: str
    days: int
    candles: List[CandleData]
    indicators: IndicatorData


# ══════════════════════════════════════════════════════════════════
# SIGNALS
# ══════════════════════════════════════════════════════════════════

class SignalIndicators(BaseModel):
    """Indicator context for signal."""
    rsi: Optional[float]
    rsi_zone: str
    macd: Optional[float]
    macd_signal: Optional[float]
    macd_hist: Optional[float]
    macd_bias: str
    bb_pctb: Optional[float]
    bb_zone: str
    in_uptrend: bool
    volume_ratio: Optional[float]
    volume_note: str


class SignalThresholds(BaseModel):
    """Confidence thresholds for 5-level signal system."""
    buy_high: float      # >= 0.65: Strong BUY
    buy_medium: float    # >= 0.55: Moderate BUY
    buy_low: float       # >= 0.45: Weak signal


class SignalResponse(BaseModel):
    """Response for GET /api/signal/{symbol}."""
    symbol: str
    date: str
    close: Optional[float]
    buy_confidence: float
    sell_confidence: Optional[float]  # None if SELL model not available
    verdict: str
    verdict_color: str
    description: str
    active_signals: List[str]
    indicators: SignalIndicators
    thresholds: SignalThresholds


# ══════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════

class SummarySignal(BaseModel):
    """Summary signal in top 10 list."""
    symbol: str
    close: Optional[float]
    date: str
    rsi: Optional[float]
    confidence: float
    signals: List[str]
    in_uptrend: bool


class SummaryResponse(BaseModel):
    """Response for GET /api/summary."""
    top_signals: List[SummarySignal]
    total_above_threshold: int
    threshold_used: float


# ══════════════════════════════════════════════════════════════════
# POSITION MANAGEMENT
# ══════════════════════════════════════════════════════════════════

class PositionCheckRequest(BaseModel):
    """Request to check if a position should exit."""
    symbol: str
    entry_date: str  # ISO format: "2025-05-01"
    entry_price: float
    current_price: float
    current_buy_conf: float


class ExitStatusResponse(BaseModel):
    """Response for POST /api/positions/exit-check."""
    should_exit: bool
    reason: Optional[str] = None
    exit_type: Optional[str] = None  # "time_based", "stop_loss", "signal_decay"
    days_held: int
    days_remaining: int
    current_return_pct: float
    distance_to_stop_loss_pct: float
    risks: List[str]
