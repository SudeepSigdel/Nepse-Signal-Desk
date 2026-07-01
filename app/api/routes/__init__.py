"""API routes, organized by resource type."""

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.holdings import router as holdings_router
from app.api.routes.performance import router as performance_router
from app.api.routes.positions import router as positions_router
from app.api.routes.signals import router as signals_router
from app.api.routes.stocks import router as stocks_router
from app.api.routes.watchlist import router as watchlist_router

__all__ = [
    "health_router",
    "stocks_router",
    "signals_router",
    "positions_router",
    "performance_router",
    "auth_router",
    "watchlist_router",
    "holdings_router",
]
