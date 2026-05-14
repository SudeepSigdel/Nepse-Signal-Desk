"""
API routes: health, stocks, and signals endpoints.
Organized by resource type for clarity and maintainability.
"""

from fastapi import APIRouter, HTTPException
import pandas as pd
from datetime import datetime

from app.schemas import (
    HealthResponse, StocksListResponse, StockData, StockDetailResponse, 
    CandleData, IndicatorData, SignalResponse, SummaryResponse, SummarySignal,
    PositionCheckRequest, ExitStatusResponse
)
from app.config import settings
from app.constants import THRESHOLD_MEDIUM, THRESHOLD_LOW
from app.data_loader import DataLoader
from app.signal_service import SignalService, safe_val
from app.exit_rules import ExitRulesService
from app.logging_config import get_logger

logger = get_logger(__name__)

# Create routers
health_router = APIRouter()
stocks_router = APIRouter()
signals_router = APIRouter()
positions_router = APIRouter()

# Initialize exit rules service (singleton pattern)
exit_rules = ExitRulesService(
    exit_days=10,
    stop_loss_pct=5.0,
    min_buy_conf=0.45
)


# ══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════════

@health_router.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint for monitoring."""
    loader = DataLoader()
    
    return HealthResponse(
        status="healthy" if loader.is_ready() else "degraded",
        version=settings.api_version,
        environment=settings.env,
        model_loaded=loader.model is not None,
        features_loaded=loader.features_df is not None,
        symbols_count=len(loader.all_symbols),
    )


# ══════════════════════════════════════════════════════════════════
# STOCKS
# ══════════════════════════════════════════════════════════════════

@stocks_router.get("/api/stocks", response_model=StocksListResponse)
def get_stocks():
    """Get all stocks above confidence threshold, ranked by confidence."""
    loader = DataLoader()
    signal_service = SignalService(loader)
    
    if not loader.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    results = []
    
    for symbol in loader.all_symbols:
        confidence = signal_service.compute_confidence(symbol)
        if confidence is None or confidence < THRESHOLD_LOW:
            continue
        
        latest_row = loader.get_latest_row(symbol)
        if latest_row is None:
            continue
        
        tier = signal_service.get_tier(confidence)
        
        results.append(StockData(
            symbol=symbol,
            date=latest_row["Date"].strftime("%Y-%m-%d"),
            close=safe_val(latest_row.get("Close")),
            rsi=safe_val(latest_row.get("RSI_14")),
            confidence=confidence,
            tier=tier
        ))
    
    results.sort(key=lambda x: x.confidence, reverse=True)
    return StocksListResponse(stocks=results, count=len(results))


@stocks_router.get("/api/stocks/{symbol}", response_model=StockDetailResponse)
def get_stock_details(symbol: str, days: int = 180):
    """Get detailed stock data with indicators for charting."""
    loader = DataLoader()
    
    symbol = symbol.upper()
    days = max(1, min(days, 2000))
    
    if symbol not in loader.all_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    
    stock_df = loader.get_stock_data(symbol, days)
    if stock_df is None or stock_df.empty:
        raise HTTPException(status_code=404, detail=f"Data for symbol '{symbol}' not found")
    
    candles = []
    indicators_data = {
        "sma20": [],
        "bb_upper": [],
        "bb_lower": [],
        "bb_mid": [],
        "ema12": [],
        "ema26": [],
        "rsi": [],
        "macd": [],
        "macd_sig": [],
        "macd_hist": [],
        "volume": [],
        "dates": [],
    }
    
    for _, row in stock_df.iterrows():
        date_str = str(row["Date"].date())
        indicators_data["dates"].append(date_str)
        
        candles.append(CandleData(
            t=date_str,
            o=safe_val(row.get("Open")),
            h=safe_val(row.get("High")),
            l=safe_val(row.get("Low")),
            c=safe_val(row.get("Close")),
            v=safe_val(row.get("Volume")),
        ))
        
        indicators_data["sma20"].append(safe_val(row.get("SMA_20")))
        indicators_data["bb_upper"].append(safe_val(row.get("BB_Upper")))
        indicators_data["bb_lower"].append(safe_val(row.get("BB_Lower")))
        indicators_data["bb_mid"].append(safe_val(row.get("BB_Middle")))
        indicators_data["ema12"].append(safe_val(row.get("EMA_12")))
        indicators_data["ema26"].append(safe_val(row.get("EMA_26")))
        
        indicators_data["rsi"].append(safe_val(row.get("RSI_14")))
        indicators_data["macd"].append(safe_val(row.get("MACD")))
        indicators_data["macd_sig"].append(safe_val(row.get("MACD_Signal")))
        macd_hist = (safe_val(row.get("MACD")) or 0) - (safe_val(row.get("MACD_Signal")) or 0)
        indicators_data["macd_hist"].append(round(macd_hist, 4))
        indicators_data["volume"].append(safe_val(row.get("Volume")))
    
    indicators = IndicatorData(**indicators_data)
    
    return StockDetailResponse(
        symbol=symbol,
        days=days,
        candles=candles,
        indicators=indicators,
    )


# ══════════════════════════════════════════════════════════════════
# SIGNALS
# ══════════════════════════════════════════════════════════════════

@signals_router.get("/api/signal/{symbol}", response_model=SignalResponse)
def get_signal(symbol: str):
    """Get ML confidence score and signal interpretation for a stock."""
    loader = DataLoader()
    signal_service = SignalService(loader)
    
    symbol = symbol.upper()
    
    if symbol not in loader.all_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    
    signal_data = signal_service.get_signal(symbol)
    if signal_data is None:
        raise HTTPException(status_code=404, detail=f"Insufficient data for symbol '{symbol}'")
    
    return SignalResponse(**signal_data)


@signals_router.get("/api/summary", response_model=SummaryResponse)
def get_summary():
    """Get top 10 high-confidence signals across all stocks."""
    loader = DataLoader()
    signal_service = SignalService(loader)
    
    if not loader.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded")
    
    results = []
    
    for symbol in loader.all_symbols:
        confidence = signal_service.compute_confidence(symbol)
        if confidence is None or confidence < THRESHOLD_MEDIUM:
            continue
        
        latest_row = loader.get_latest_row(symbol)
        if latest_row is None:
            continue
        
        active_signals = signal_service.get_active_signals(latest_row)
        in_uptrend = bool(safe_val(latest_row.get("In_uptrend")))
        
        results.append(SummarySignal(
            symbol=symbol,
            close=safe_val(latest_row.get("Close")),
            date=str(latest_row["Date"].date()),
            rsi=safe_val(latest_row.get("RSI_14")),
            confidence=round(confidence, 3),
            signals=active_signals,
            in_uptrend=in_uptrend,
        ))
    
    results.sort(key=lambda x: x.confidence, reverse=True)
    
    return SummaryResponse(
        top_signals=results[:10],
        total_above_threshold=len(results),
        threshold_used=THRESHOLD_MEDIUM,
    )


# ══════════════════════════════════════════════════════════════════
# POSITIONS
# ══════════════════════════════════════════════════════════════════

@positions_router.post("/api/positions/exit-check", response_model=ExitStatusResponse)
def check_position_exit(request: PositionCheckRequest):
    """
    Check if an active position should be exited based on exit rules.
    
    Exit triggers:
    - Time-based: After 10 days
    - Stop-loss: Price down 5% from entry
    - Signal decay: Buy confidence below 0.45
    """
    try:
        entry_date = datetime.fromisoformat(request.entry_date)
        
        # Check exit signal
        exit_signal = exit_rules.check_exit(
            entry_date=entry_date,
            entry_price=request.entry_price,
            current_price=request.current_price,
            current_buy_conf=request.current_buy_conf
        )
        
        # Get detailed status for UI
        status = exit_rules.get_exit_status(
            entry_date=entry_date,
            entry_price=request.entry_price,
            current_price=request.current_price,
            current_buy_conf=request.current_buy_conf
        )
        
        return ExitStatusResponse(
            should_exit=exit_signal.should_exit,
            reason=exit_signal.reason,
            exit_type=exit_signal.reason_type,
            days_held=exit_signal.days_held,
            days_remaining=max(0, 10 - exit_signal.days_held),
            current_return_pct=exit_signal.exit_return_pct,
            distance_to_stop_loss_pct=status['distance_to_stop_loss_pct'],
            risks=status['risks']
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error checking position exit: {e}")
        raise HTTPException(status_code=400, detail=str(e))
