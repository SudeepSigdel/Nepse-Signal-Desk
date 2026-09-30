"""Shared rate limiter (slowapi/limits), keyed by client IP.

Kept in its own module so both app/main.py (middleware + exception handler)
and individual routers (the @limiter.limit(...) decorators) can import the
same Limiter instance without a circular import.

With REDIS_URL set, counters live in Redis so limits hold across uvicorn
workers and restarts; if Redis is unreachable, slowapi falls back to
per-process memory instead of failing requests.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

if settings.redis_url:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        in_memory_fallback_enabled=True,
        swallow_errors=True,
    )
else:
    limiter = Limiter(key_func=get_remote_address)
