"""
NEPSE AI Signals API - Main entry point.
Routes are imported from the routes module for clean organization.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.routes import health_router, stocks_router, signals_router, positions_router
from app.data_loader import DataLoader

# ─── Setup logging ──────────────────────────────────────────
setup_logging()
logger = get_logger(__name__)

logger.info(f"Starting NEPSE AI Signals API v{settings.api_version}")
logger.info(f"Environment: {settings.env}")
logger.info(f"Debug: {settings.debug}")

# ─── Create FastAPI app ─────────────────────────────────────
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    debug=settings.debug,
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

# ─── Initialize data on startup ────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Initialize data loader on app startup."""
    loader = DataLoader()
    if loader.is_ready():
        logger.info("✓ All data loaded successfully")
    else:
        logger.warning("⚠ Some data failed to load (degraded mode)")

# ─── Register routers ──────────────────────────────────────
app.include_router(health_router)
app.include_router(stocks_router)
app.include_router(signals_router)
app.include_router(positions_router)

logger.info("API ready")
