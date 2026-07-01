"""Per-user watchlist endpoints (persisted; replaces browser localStorage)."""

from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db_models import User, WatchlistItem
from app.schemas import WatchlistItemResponse
from app.services.auth_service import get_current_user

router = APIRouter()


def _list_items(user: User, db: Session) -> List[WatchlistItemResponse]:
    items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).order_by(WatchlistItem.created_at).all()
    return [WatchlistItemResponse(symbol=item.symbol) for item in items]


@router.get("/api/watchlist", response_model=List[WatchlistItemResponse])
def get_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _list_items(user, db)


@router.post("/api/watchlist/{symbol}", response_model=List[WatchlistItemResponse], status_code=status.HTTP_201_CREATED)
def add_to_watchlist(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    symbol = symbol.upper()
    exists = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id, WatchlistItem.symbol == symbol).first()
    if exists is None:
        db.add(WatchlistItem(user_id=user.id, symbol=symbol))
        db.commit()
    return _list_items(user, db)


@router.delete("/api/watchlist/{symbol}", response_model=List[WatchlistItemResponse])
def remove_from_watchlist(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    symbol = symbol.upper()
    db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id, WatchlistItem.symbol == symbol).delete()
    db.commit()
    return _list_items(user, db)
