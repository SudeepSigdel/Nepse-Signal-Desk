# ════════════════════════════════════════════════════════════
# app/config.py — Centralized Configuration
# Loads settings from environment variables
# ════════════════════════════════════════════════════════════

import os
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings, loaded from .env file and environment variables.
    """

    # ─── Environment ───────────────────────────────────────
    env: str = "development"  # development | staging | production
    debug: bool = True
    log_level: str = "INFO"

    # ─── Paths ─────────────────────────────────────────────
    # Project root — defaults to parent of app/ folder
    project_root: Path = Path(__file__).resolve().parent.parent
    data_processed_dir: Path = Field(default="data/processed")
    model_dir: Path = Field(default="data/processed/models")
    raw_data_dir: Path = Field(default="data/raw")
    reference_data_dir: Path = Field(default="data/reference")

    # ─── API ────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "NEPSE AI Signals"
    api_version: str = "0.1.0"

    # ─── CORS ────────────────────────────────────────────────
    # Kept as a plain string field (not List[str]) because pydantic-settings
    # tries to JSON-decode env vars for list-typed fields before any validator
    # runs, which breaks a plain comma-separated value like
    # "http://a.com,http://b.com". Use the `cors_origins` property below for
    # the parsed list.
    cors_origins_csv: str = Field(default="*", validation_alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_csv.split(",") if origin.strip()]

    # ─── Security ────────────────────────────────────────────
    secret_key: str = "dev-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ─── Database ────────────────────────────────────────────
    database_url: str = ""

    # ─── Google OAuth ──────────────────────────────────────────
    # Empty client_id disables the Google login routes; email/password still works.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    frontend_url: str = "http://localhost:3000"

    # ─── Scraper ─────────────────────────────────────────────
    scraper_source: str = "sharesansar"
    scraper_delay: float = 0.2

    # ─── ML Model Family ────────────────────────────────────
    # random_forest matches the current checked-in model artifacts.
    # Set MODEL_FAMILY=xgboost to switch to XGBoost artifacts when present.
    model_family: str = "random_forest"

    # Stock universe quality gates. These keep very thin symbols out of the
    # dashboard while still showing all model-ready liquid stocks.
    liquidity_lookback_days: int = 252
    min_liquid_trading_days: int = 120
    min_median_turnover: float = 50000.0
    min_median_volume: float = 100.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # .env is shared with standalone scripts (e.g. scrapper/nepse_scraper.py
        # reads NEPSE_SCRAPER_START_DATE via os.getenv directly) that don't
        # correspond to a Settings field — without this, pydantic-settings
        # raises on any env var it doesn't recognize.
        extra="ignore",
    )


# ─── Singleton instance (use this in your app) ──────────────
settings = Settings()

if settings.env == "production" and "*" in settings.cors_origins:
    raise RuntimeError(
        "Wildcard CORS origin ('*') is forbidden when ENV=production — "
        "set CORS_ORIGINS to an explicit comma-separated list of allowed origins."
    )

# ─── Resolve full paths ────────────────────────────────────
# Convert relative paths to absolute (relative to project root)
settings.data_processed_dir = (
    settings.project_root / settings.data_processed_dir
    if not settings.data_processed_dir.is_absolute()
    else settings.data_processed_dir
)
settings.model_dir = (
    settings.project_root / settings.model_dir
    if not settings.model_dir.is_absolute()
    else settings.model_dir
)
settings.raw_data_dir = (
    settings.project_root / settings.raw_data_dir
    if not settings.raw_data_dir.is_absolute()
    else settings.raw_data_dir
)
settings.reference_data_dir = (
    settings.project_root / settings.reference_data_dir
    if not settings.reference_data_dir.is_absolute()
    else settings.reference_data_dir
)
