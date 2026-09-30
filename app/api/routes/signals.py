"""Signal (ML confidence) endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_data_version, get_response_cache, get_signal_service, get_stock_repository
from app.cache import ResponseCache, cached_json_response
from app.constants import THRESHOLD_MEDIUM
from app.repositories.stock_repository import StockRepository
from app.schemas import SignalResponse, SummaryResponse, SummarySignal
from app.services.signal_service import SignalService, safe_val

router = APIRouter()


@router.get("/api/signal/{symbol}/both")
def get_signal_both(
    request: Request,
    symbol: str,
    stocks: StockRepository = Depends(get_stock_repository),
    signal_service: SignalService = Depends(get_signal_service),
    cache: ResponseCache = Depends(get_response_cache),
    version: str = Depends(get_data_version),
):
    """Return signal payloads for both model families in one response."""
    symbol = symbol.upper()
    if symbol not in stocks.all_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    def build() -> bytes:
        payload = {
            "xgboost": signal_service.get_signal(symbol, "xgboost"),
            "random_forest": signal_service.get_signal(symbol, "random_forest"),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()

    return cached_json_response(request, cache, f"signal-both:{version}:{symbol}", build)


@router.get("/api/signal/{symbol}", response_model=SignalResponse)
def get_signal(
    request: Request,
    symbol: str,
    family: str | None = None,
    stocks: StockRepository = Depends(get_stock_repository),
    signal_service: SignalService = Depends(get_signal_service),
    cache: ResponseCache = Depends(get_response_cache),
    version: str = Depends(get_data_version),
):
    """Get ML confidence score and signal interpretation for a stock."""
    symbol = symbol.upper()

    if symbol not in stocks.all_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    def build() -> SignalResponse:
        signal_data = signal_service.get_signal(symbol, family)
        if signal_data is None:
            raise HTTPException(status_code=404, detail=f"Insufficient data for symbol '{symbol}'")
        return SignalResponse(**signal_data)

    return cached_json_response(request, cache, f"signal:{version}:{symbol}:{family or ''}", build)


@router.get("/api/summary", response_model=SummaryResponse)
def get_summary(
    request: Request,
    family: str | None = None,
    stocks: StockRepository = Depends(get_stock_repository),
    signal_service: SignalService = Depends(get_signal_service),
    cache: ResponseCache = Depends(get_response_cache),
    version: str = Depends(get_data_version),
):
    """Get top 10 high-confidence signals across all stocks."""
    return cached_json_response(
        request, cache, f"summary:{version}:{family or ''}", lambda: _build_summary(family, stocks, signal_service)
    )


def _build_summary(family: str | None, stocks: StockRepository, signal_service: SignalService) -> SummaryResponse:
    if not stocks.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded")

    results = []

    for symbol in stocks.all_symbols:
        if family:
            confidence = signal_service.compute_confidence_for_family(symbol, family)
        else:
            confidence = signal_service.compute_confidence(symbol)
        if confidence is None or confidence < THRESHOLD_MEDIUM:
            continue

        latest_row = stocks.get_latest_row(symbol)
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
