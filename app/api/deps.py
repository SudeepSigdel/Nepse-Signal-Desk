"""
FastAPI dependency providers.

Repositories and services are constructed once at startup (see app/main.py's
lifespan hook) and stored on app.state; these providers just hand out that
shared instance per request instead of every route constructing its own.
"""

import glob
import os
import time

from fastapi import Request

from app.cache import ResponseCache
from app.config import settings

from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.model_repository import ModelRepository
from app.repositories.sector_repository import SectorRepository
from app.repositories.stock_repository import StockRepository
from app.services.exit_rules import ExitRulesService
from app.services.paper_trading_service import PaperTradingService
from app.services.price_feed import PriceFeed
from app.services.signal_service import SignalService


def get_model_repository(request: Request) -> ModelRepository:
    return request.app.state.model_repository


def get_evaluation_repository(request: Request) -> EvaluationRepository:
    return request.app.state.evaluation_repository


def get_stock_repository(request: Request) -> StockRepository:
    return request.app.state.stock_repository


def get_sector_repository(request: Request) -> SectorRepository:
    return request.app.state.sector_repository


def get_signal_service(request: Request) -> SignalService:
    return request.app.state.signal_service


def get_exit_rules_service(request: Request) -> ExitRulesService:
    return request.app.state.exit_rules_service


def get_price_feed(request: Request) -> PriceFeed:
    return request.app.state.price_feed


def get_paper_trading_service(request: Request) -> PaperTradingService:
    return request.app.state.paper_trading_service


def get_response_cache(request: Request) -> ResponseCache:
    return request.app.state.response_cache


_version_memo: dict = {"at": 0.0, "value": ""}


def get_data_version(request: Request) -> str:
    """
    Identifies the market data + models currently being served; part of every
    cache key, so a daily pipeline refresh naturally invalidates old entries.
    Re-stat'ed at most every few seconds.
    """
    now = time.monotonic()
    if now - _version_memo["at"] > 5.0 or not _version_memo["value"]:
        parquet = request.app.state.stock_repository.data_version() or 0
        models = [os.path.getmtime(p) for p in glob.glob(str(settings.model_dir / "model_latest*.pkl"))]
        _version_memo["value"] = f"{parquet:.0f}-{max(models, default=0):.0f}"
        _version_memo["at"] = now
    return _version_memo["value"]
