"""Model validation / backtest performance endpoints (powers the Trust page)."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_evaluation_repository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.model_repository import normalize_model_family
from app.schemas import ModelPerformanceResponse

router = APIRouter()


@router.get("/api/model-performance", response_model=ModelPerformanceResponse)
def get_model_performance(
    family: str | None = None,
    evaluation: EvaluationRepository = Depends(get_evaluation_repository),
):
    """Walk-forward validation, calibration, and backtested returns for a model family."""
    fam = normalize_model_family(family)
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
