"""Model validation / backtest performance endpoints (powers the Trust page)."""

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import get_data_version, get_evaluation_repository, get_response_cache
from app.cache import ResponseCache, cached_json_response
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.model_repository import normalize_model_family
from app.schemas import ModelPerformanceResponse

router = APIRouter()


@router.get("/api/model-performance", response_model=ModelPerformanceResponse)
def get_model_performance(
    request: Request,
    family: str | None = None,
    evaluation: EvaluationRepository = Depends(get_evaluation_repository),
    cache: ResponseCache = Depends(get_response_cache),
    version: str = Depends(get_data_version),
):
    """Walk-forward validation, calibration, and backtested returns for a model family."""
    fam = normalize_model_family(family)

    def build() -> ModelPerformanceResponse:
        data = evaluation.get(fam)
        if data is None:
            raise HTTPException(status_code=503, detail=f"No evaluation data available for family '{fam}'")
        return ModelPerformanceResponse(
            family=fam,
            buy=data["buy"],
            sell=data["sell"],
            thresholds=data["thresholds"],
            strategy_comparison=data["strategy_comparison"],
        )

    return cached_json_response(request, cache, f"performance:{version}:{fam}", build)
