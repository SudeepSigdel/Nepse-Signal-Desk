"""Stock listing and detail endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_sector_repository, get_signal_service, get_stock_repository
from app.repositories.sector_repository import SectorRepository
from app.repositories.stock_repository import StockRepository
from app.schemas import (
    CandleData, IndicatorData, StockData, StockDetailResponse, StocksListResponse,
)
from app.services.signal_service import SignalService, safe_val

router = APIRouter()


@router.get("/api/stocks", response_model=StocksListResponse)
def get_stocks(
    family: str | None = None,
    signal_service: SignalService = Depends(get_signal_service),
    stocks: StockRepository = Depends(get_stock_repository),
    sectors: SectorRepository = Depends(get_sector_repository),
):
    """Get all liquid, model-ready stocks, ranked by BUY confidence."""
    if not stocks.is_ready():
        raise HTTPException(status_code=503, detail="Data not loaded")

    results = []

    for symbol in stocks.all_symbols:
        if not signal_service.is_liquid_enough(symbol):
            continue

        latest_row = stocks.get_latest_row(symbol)
        if latest_row is None:
            continue

        if family == "both":
            conf_x = signal_service.compute_confidence_for_family(symbol, "xgboost")
            conf_rf = signal_service.compute_confidence_for_family(symbol, "random_forest")
            available = [c for c in (conf_x, conf_rf) if c is not None]
            if not available:
                continue
            confidence = round(sum(available) / len(available), 4)
            buy_confidence, rf_confidence = conf_x, conf_rf
            sell_confidence = signal_service.compute_sell_confidence_for_family(symbol, "xgboost")
        else:
            confidence = signal_service.compute_confidence_for_family(symbol, family)
            if confidence is None:
                continue
            buy_confidence, rf_confidence = confidence, None
            sell_confidence = signal_service.compute_sell_confidence_for_family(symbol, family)

        tier = signal_service.get_tier(confidence)
        sector_info = sectors.get(symbol)
        results.append(StockData(
            symbol=symbol,
            date=latest_row["Date"].strftime("%Y-%m-%d"),
            close=safe_val(latest_row.get("Close")),
            rsi=safe_val(latest_row.get("RSI_14")),
            volume_ratio=safe_val(latest_row.get("Volume_ratio")),
            change_pct=safe_val(latest_row.get("Percent Change")),
            turnover=safe_val(latest_row.get("Turnover")),
            sector=sector_info.sector if sector_info else None,
            sub_index=sector_info.sub_index if sector_info else None,
            confidence=confidence,
            buy_confidence=buy_confidence,
            rf_confidence=rf_confidence,
            sell_confidence=sell_confidence,
            verdict=signal_service.verdict_code(confidence, sell_confidence),
            tier=tier,
        ))

    results.sort(key=lambda x: x.confidence, reverse=True)
    return StocksListResponse(stocks=results, count=len(results))


@router.get("/api/stocks/{symbol}", response_model=StockDetailResponse)
def get_stock_details(
    symbol: str,
    days: int = 180,
    stocks: StockRepository = Depends(get_stock_repository),
):
    """Get detailed stock data with indicators for charting."""
    symbol = symbol.upper()
    days = max(1, min(days, 2000))

    if symbol not in stocks.all_symbols:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    stock_df = stocks.get_stock_data(symbol, days)
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
