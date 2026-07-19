"""
NEPSE AI Signals API - Main entry point.
Routes are imported from the routes module for clean organization.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.middleware import RequestIDMiddleware
from app.rate_limit import limiter
from app.api.routes import (
    auth_router,
    health_router,
    holdings_router,
    performance_router,
    positions_router,
    signals_router,
    stocks_router,
    watchlist_router,
)
from app.db import engine
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.model_repository import ModelRepository
from app.repositories.sector_repository import SectorRepository
from app.repositories.stock_repository import StockRepository
from app.services.exit_rules import ExitRulesService
from app.services.signal_service import SignalService

# ─── Setup logging ──────────────────────────────────────────
setup_logging()
logger = get_logger(__name__)

logger.info(f"Starting NEPSE AI Signals API v{settings.api_version}")
logger.info(f"Environment: {settings.env}")
logger.info(f"Debug: {settings.debug}")


# ─── Lifespan (replaces deprecated on_event) ───────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load repositories/services once at startup and expose them via app.state."""
    model_repository = ModelRepository(
        model_dir=settings.model_dir,
        data_processed_dir=settings.data_processed_dir,
        default_family=settings.model_family,
    )
    model_repository.load()

    stock_repository = StockRepository(
        features_path=settings.data_processed_dir / "all_stocks_features.parquet"
    )
    stock_repository.load()

    sector_repository = SectorRepository(reference_data_dir=settings.reference_data_dir)
    sector_repository.load()

    evaluation_repository = EvaluationRepository(
        data_processed_dir=settings.data_processed_dir,
        project_root=settings.project_root,
    )
    evaluation_repository.load()

    # Schema is owned by Alembic migrations now (see alembic/versions/) —
    # run `alembic upgrade head` after pulling changes rather than relying
    # on the app to create/alter tables at startup.
    if engine is not None:
        with engine.connect():
            pass
        logger.info("Database connection OK")
    else:
        logger.warning("DATABASE_URL not set — accounts/watchlist/holdings endpoints will fail")

    if stock_repository.features_df is not None:
        buy_bundle = model_repository.get_buy_bundle()
        if buy_bundle and buy_bundle.get("features"):
            missing = set(buy_bundle["features"]) - set(stock_repository.features_df.columns)
            if missing:
                logger.error("Model expects features missing from parquet data: %s", sorted(missing))

        relative_bundle = model_repository.get_relative_bundle()
        if relative_bundle and relative_bundle.get("features"):
            missing = set(relative_bundle["features"]) - set(stock_repository.features_df.columns)
            if missing:
                logger.error("Relative Strength model expects features missing from parquet data: %s", sorted(missing))

    app.state.model_repository = model_repository
    app.state.stock_repository = stock_repository
    app.state.sector_repository = sector_repository
    app.state.evaluation_repository = evaluation_repository
    app.state.signal_service = SignalService(model_repository, stock_repository)
    app.state.exit_rules_service = ExitRulesService(
        exit_days=10,
        stop_loss_pct=5.0,
        min_buy_conf=0.45,
    )

    if model_repository.is_ready() and stock_repository.is_ready():
        logger.info("✓ All data loaded successfully")
    else:
        logger.warning("⚠ Some data failed to load (degraded mode)")

    yield
    # Cleanup (if needed) goes here


# ─── Create FastAPI app ─────────────────────────────────────
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# ─── Add CORS middleware ───────────────────────────────────
logger.info(f"CORS origins: {settings.cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
# Required by Authlib's Starlette OAuth client to store transient state/nonce
# during the Google login redirect round-trip.
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# ─── Rate limiting (brute-force protection on auth) ────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ─── Register routers ──────────────────────────────────────
app.include_router(health_router)
app.include_router(stocks_router)
app.include_router(signals_router)
app.include_router(positions_router)
app.include_router(performance_router)
app.include_router(auth_router)
app.include_router(watchlist_router)
app.include_router(holdings_router)

logger.info("API ready")
