"""Paper-trading endpoints: virtual accounts, orders, quotes, fee previews, leaderboard."""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_paper_trading_service, get_price_feed, get_response_cache
from app.cache import ResponseCache, cached_json_response
from app.db import get_db
from app.db_models import PaperAccount, PaperOrder, User
from app.rate_limit import limiter
from app.schemas import (
    FeeBreakdownResponse,
    FeePreviewRequest,
    LeaderboardEntry,
    PaperAccountCreate,
    PaperAccountResponse,
    PaperEquityPoint,
    PaperOrderCreate,
    PaperOrderResponse,
    QuoteResponse,
)
from app.services.auth_service import get_current_user
from app.services.paper_trading_service import PaperTradingService, as_utc
from app.services.price_feed import PriceFeed
from app.trading.fees import buy_cost, sell_proceeds
from app.trading.rules import is_market_open

router = APIRouter(prefix="/api/paper", tags=["paper-trading"])


def _order_response(order: PaperOrder) -> PaperOrderResponse:
    return PaperOrderResponse(
        id=order.id,
        account_id=order.account_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        qty=order.qty,
        limit_price=order.limit_price,
        status=order.status,
        reject_reason=order.reject_reason,
        reserved_cash=order.reserved_cash,
        created_at=as_utc(order.created_at).isoformat(),
        filled_at=as_utc(order.filled_at).isoformat() if order.filled_at else None,
        fill_price=order.fill_price,
        price_source=order.price_source,
        fees=FeeBreakdownResponse(**json.loads(order.fees_json)) if order.fees_json else None,
        realized_pnl=order.realized_pnl,
    )


def _owned_account(
    account_id: int, user: User, db: Session, service: PaperTradingService, lock: bool = False
) -> PaperAccount:
    account = service.get_account(db, user, account_id, lock=lock)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper account not found")
    return account


@router.get("/accounts", response_model=List[PaperAccountResponse])
def list_accounts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    return [service.account_summary(a) for a in service.list_accounts(db, user)]


@router.post("/accounts", response_model=PaperAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: PaperAccountCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    try:
        account = service.create_account(db, user, payload.name, payload.starting_cash)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return service.account_summary(account)


@router.get("/accounts/{account_id}", response_model=PaperAccountResponse)
def get_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    return service.account_summary(_owned_account(account_id, user, db, service))


@router.post("/accounts/{account_id}/reset", response_model=PaperAccountResponse)
def reset_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    account = service.reset_account(db, _owned_account(account_id, user, db, service, lock=True))
    return service.account_summary(account)


@router.get("/accounts/{account_id}/orders", response_model=List[PaperOrderResponse])
def list_orders(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    account = _owned_account(account_id, user, db, service)
    return [_order_response(o) for o in sorted(account.orders, key=lambda o: o.id, reverse=True)]


@router.post("/accounts/{account_id}/orders", response_model=PaperOrderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def place_order(
    request: Request,
    account_id: int,
    payload: PaperOrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    account = _owned_account(account_id, user, db, service, lock=True)
    order = service.place_order(
        db, account, payload.symbol, payload.side, payload.order_type, payload.qty, payload.limit_price
    )
    return _order_response(order)


# POST rather than DELETE: CORS on this API only allows GET/POST.
@router.post("/orders/{order_id}/cancel", response_model=PaperOrderResponse)
def cancel_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    order = service.get_order(db, user, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    try:
        return _order_response(service.cancel_order(db, order))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/accounts/{account_id}/equity", response_model=List[PaperEquityPoint])
def equity_history(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    account = _owned_account(account_id, user, db, service)
    return [
        PaperEquityPoint(date=s.date.isoformat(), cash=s.cash, equity=s.equity)
        for s in service.equity_history(db, account)
    ]


@router.get("/quote/{symbol}", response_model=QuoteResponse)
def quote(symbol: str, feed: PriceFeed = Depends(get_price_feed)):
    result = feed.get_quote(symbol)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No price data for {symbol.upper()}")
    return QuoteResponse(**result.to_dict(), market_open=is_market_open())


@router.post("/fee-preview", response_model=FeeBreakdownResponse)
def fee_preview(payload: FeePreviewRequest):
    if payload.side == "buy":
        return FeeBreakdownResponse(**buy_cost(payload.price, payload.qty).to_dict())
    avg_cost = payload.avg_cost if payload.avg_cost is not None else payload.price
    return FeeBreakdownResponse(
        **sell_proceeds(payload.price, payload.qty, avg_cost, payload.holding_days).to_dict()
    )


@router.get("/leaderboard", response_model=List[LeaderboardEntry])
def leaderboard(
    request: Request,
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
    cache: ResponseCache = Depends(get_response_cache),
):
    # Marks every account to market, so it's recomputed at most once a minute.
    def build() -> bytes:
        rows = [LeaderboardEntry(rank=i, **row).model_dump() for i, row in enumerate(service.leaderboard(db), 1)]
        return json.dumps(rows, separators=(",", ":")).encode()

    return cached_json_response(request, cache, "paper-leaderboard", build, ttl=60, max_age=30)
