"""Health check endpoint."""

from fastapi import APIRouter, Depends

from app.api.deps import get_model_repository, get_stock_repository
from app.config import settings
from app.repositories.model_repository import ModelRepository
from app.repositories.stock_repository import StockRepository
from app.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(
    models: ModelRepository = Depends(get_model_repository),
    stocks: StockRepository = Depends(get_stock_repository),
):
    """Health check endpoint for monitoring."""
    ready = models.is_ready() and stocks.is_ready()
    return HealthResponse(
        status="healthy" if ready else "degraded",
        version=settings.api_version,
        environment=settings.env,
        model_loaded=models.is_ready(),
        features_loaded=stocks.features_df is not None,
        symbols_count=len(stocks.all_symbols),
    )
