# ════════════════════════════════════════════════════════════
# app/logging_config.py — Structured Logging Setup
# Provides JSON-formatted logs for production, readable logs for dev
# ════════════════════════════════════════════════════════════

import json
import logging
import sys
from typing import Any, Dict

from app.config import settings


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON.
    Useful for log aggregation services (ELK, Datadog, etc.).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class ReadableFormatter(logging.Formatter):
    """
    Simple, human-readable formatter for development.
    """

    def format(self, record: logging.LogRecord) -> str:
        return (
            f"[{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}] "
            f"{record.levelname:<8} {record.name:<25} "
            f"{record.getMessage()}"
        )


def setup_logging() -> None:
    """
    Configure logging for the application.
    - JSON format in production for log aggregation
    - Readable format in development for debugging
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Choose formatter based on environment
    if settings.env == "production":
        formatter = JSONFormatter()
    else:
        formatter = ReadableFormatter()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Optionally add file handler (in production)
    if settings.env == "production":
        log_file = settings.project_root / "outputs" / "logs" / "api.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(settings.log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("pandas").setLevel(logging.WARNING)


# ─── Get logger for use in modules ──────────────────────────
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    Usage: logger = get_logger(__name__)
    """
    return logging.getLogger(name)
