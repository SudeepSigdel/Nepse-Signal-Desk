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

    # ─── API ────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "NEPSE AI Signals"
    api_version: str = "0.1.0"

    # ─── CORS ────────────────────────────────────────────────
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5000",
        "http://localhost:8080",
    ]

    # ─── Rate Limiting ──────────────────────────────────────
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 100

    # ─── Database ────────────────────────────────────────────
    database_url: str = ""  # Empty for MVP (no DB required)

    # ─── Security ────────────────────────────────────────────
    secret_key: str = "dev-key-change-in-production"
    algorithm: str = "HS256"

    # ─── Email (for Beta+) ──────────────────────────────────
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    sender_email: str = "noreply@nepse-signals.com"

    # ─── External Services ──────────────────────────────────
    sentry_dsn: str = ""  # Optional error tracking

    # ─── Scraper ─────────────────────────────────────────────
    scraper_source: str = "sharesansar"
    scraper_delay: float = 0.2

    # ─── Monitoring ──────────────────────────────────────────
    monitoring_enabled: bool = False
    metrics_port: int = 9090

    # ─── Feature Flags ──────────────────────────────────────
    enable_signal_history: bool = False
    enable_user_alerts: bool = False
    enable_explainability: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# ─── Singleton instance (use this in your app) ──────────────
settings = Settings()

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
