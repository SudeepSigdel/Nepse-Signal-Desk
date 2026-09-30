"""Trading-agent endpoints: backtest reports and the live bots' paper accounts."""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_paper_trading_service, get_response_cache
from app.cache import ResponseCache, cached_json_response
from app.config import settings
from app.db import get_db
from app.db_models import PaperAccount
from app.repositories.model_repository import normalize_model_family
from app.schemas import LiveAgentResponse
from app.services.paper_trading_service import PaperTradingService, as_utc

router = APIRouter(prefix="/api/agents", tags=["agents"])

AGENTS_DIR = settings.project_root / "outputs" / "agents"


@router.get("/report")
def agent_report(
    request: Request, family: str | None = None, cache: ResponseCache = Depends(get_response_cache)
):
    """Backtest report written by src/09_agent_backtest.py (served as-is, cached by file version)."""
    fam = normalize_model_family(family)
    path = AGENTS_DIR / f"report_{fam}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No agent report for '{fam}' yet; run src/09_agent_backtest.py")
    version = f"{path.stat().st_mtime:.0f}"
    return cached_json_response(request, cache, f"agents-report:{fam}:{version}", path.read_bytes, max_age=300)


@router.get("/live", response_model=List[LiveAgentResponse])
def live_agents(
    db: Session = Depends(get_db),
    service: PaperTradingService = Depends(get_paper_trading_service),
):
    """The bots' real paper accounts: same fills and fees as people, with a reason on every order."""
    live_config = {}
    config_path = AGENTS_DIR / "live_agents.json"
    if config_path.exists():
        live_config = json.loads(config_path.read_text())
    out = []
    for account in db.query(PaperAccount).filter(PaperAccount.is_agent.is_(True)).order_by(PaperAccount.id):
        summary = service.account_summary(account)
        orders = sorted(account.orders, key=lambda o: o.id, reverse=True)[:25]
        out.append(
            LiveAgentResponse(
                name=account.name,
                account=summary,
                settings=live_config.get("signal_label") if account.name == "TunedSignalBot" else None,
                recent_orders=[
                    {
                        "id": o.id, "symbol": o.symbol, "side": o.side, "qty": o.qty, "status": o.status,
                        "fill_price": o.fill_price, "realized_pnl": o.realized_pnl, "note": o.note,
                        "created_at": as_utc(o.created_at).isoformat(),
                    }
                    for o in orders
                ],
            )
        )
    return out
