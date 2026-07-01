"""
FastAPI dependency providers.

Repositories and services are constructed once at startup (see app/main.py's
lifespan hook) and stored on app.state; these providers just hand out that
shared instance per request instead of every route constructing its own.
"""

from fastapi import Request

from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.model_repository import ModelRepository
from app.repositories.sector_repository import SectorRepository
from app.repositories.stock_repository import StockRepository
from app.services.exit_rules import ExitRulesService
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
