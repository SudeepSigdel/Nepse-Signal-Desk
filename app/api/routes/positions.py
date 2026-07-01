"""Position exit-check endpoint."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_exit_rules_service
from app.logging_config import get_logger
from app.schemas import ExitStatusResponse, PositionCheckRequest
from app.services.exit_rules import ExitRulesService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/api/positions/exit-check", response_model=ExitStatusResponse)
def check_position_exit(
    request: PositionCheckRequest,
    exit_rules: ExitRulesService = Depends(get_exit_rules_service),
):
    """
    Check if an active position should be exited based on exit rules.

    Exit triggers:
    - Time-based: After 10 days
    - Stop-loss: Price down 5% from entry
    - Signal decay: Buy confidence below 0.45
    """
    try:
        entry_date = datetime.fromisoformat(request.entry_date)

        exit_signal = exit_rules.check_exit(
            entry_date=entry_date,
            entry_price=request.entry_price,
            current_price=request.current_price,
            current_buy_conf=request.current_buy_conf,
        )

        status = exit_rules.get_exit_status(
            entry_date=entry_date,
            entry_price=request.entry_price,
            current_price=request.current_price,
            current_buy_conf=request.current_buy_conf,
        )

        return ExitStatusResponse(
            should_exit=exit_signal.should_exit,
            reason=exit_signal.reason,
            exit_type=exit_signal.reason_type,
            days_held=exit_signal.days_held,
            days_remaining=max(0, 10 - exit_signal.days_held),
            current_return_pct=exit_signal.exit_return_pct,
            distance_to_stop_loss_pct=status["distance_to_stop_loss_pct"],
            risks=status["risks"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error checking position exit: {e}")
        raise HTTPException(status_code=400, detail=str(e))
