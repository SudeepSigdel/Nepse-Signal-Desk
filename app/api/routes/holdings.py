"""Per-user holdings (open positions) endpoints (persisted; replaces browser localStorage)."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import Holding, User
from app.schemas import HoldingCreate, HoldingResponse
from app.services.auth_service import get_current_user

router = APIRouter()


def _to_response(holding: Holding) -> HoldingResponse:
    return HoldingResponse(
        id=holding.id,
        symbol=holding.symbol,
        entry_date=holding.entry_date,
        entry_price=holding.entry_price,
        quantity=holding.quantity,
        created_at=holding.created_at.isoformat(),
    )


@router.get("/api/holdings", response_model=List[HoldingResponse])
def list_holdings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    holdings = db.query(Holding).filter(Holding.user_id == user.id).order_by(Holding.created_at).all()
    return [_to_response(h) for h in holdings]


@router.post("/api/holdings", response_model=HoldingResponse, status_code=status.HTTP_201_CREATED)
def add_holding(payload: HoldingCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    holding = Holding(
        user_id=user.id,
        symbol=payload.symbol.upper(),
        entry_date=payload.entry_date,
        entry_price=payload.entry_price,
        quantity=payload.quantity,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return _to_response(holding)


@router.delete("/api/holdings/{holding_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_holding(holding_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    holding = db.query(Holding).filter(Holding.id == holding_id, Holding.user_id == user.id).first()
    if holding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found")
    db.delete(holding)
    db.commit()
