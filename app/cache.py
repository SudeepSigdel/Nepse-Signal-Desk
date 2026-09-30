"""
Response cache: a small in-process LRU in front of an optional shared Redis.

Market data here only changes when the daily pipeline rewrites the parquet and
model files, so list/detail responses are cached as ready-to-send JSON bytes,
keyed by a data version. A new pipeline run changes the version and the old
entries simply stop being read (and expire via TTL).

- REDIS_URL unset -> in-process memory only (per worker).
- REDIS_URL set   -> shared across workers and restarts; if Redis is down the
  cache fails open to memory and retries Redis after a short back-off, so a
  cache outage never turns into an API outage.
"""

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional

from fastapi import Request, Response

from app.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_TTL_SECONDS = 6 * 60 * 60
REDIS_RETRY_AFTER_SECONDS = 30.0
KEY_PREFIX = "nsd:v1:"


class ResponseCache:
    def __init__(self, redis_url: str = "", local_max_entries: int = 512, redis_client=None):
        self._local: "OrderedDict[str, tuple[float, bytes]]" = OrderedDict()
        self._local_max = local_max_entries
        self._lock = threading.Lock()
        self._redis = redis_client
        self._redis_down_until = 0.0
        if self._redis is None and redis_url:
            import redis  # imported lazily so the dependency is only needed when configured

            self._redis = redis.Redis.from_url(redis_url, socket_timeout=0.5, socket_connect_timeout=0.5)
        self.hits = 0
        self.misses = 0

    @property
    def backend(self) -> str:
        return "redis+memory" if self._redis is not None else "memory"

    @property
    def redis(self):
        """The Redis client when configured and not in back-off, else None."""
        if self._redis is None or time.monotonic() < self._redis_down_until:
            return None
        return self._redis

    def _redis_failed(self, exc: Exception) -> None:
        if time.monotonic() >= self._redis_down_until:
            logger.warning("Redis unavailable (%s); using in-process cache for %ss", exc, REDIS_RETRY_AFTER_SECONDS)
        self._redis_down_until = time.monotonic() + REDIS_RETRY_AFTER_SECONDS

    # ─── Local LRU ──────────────────────────────────────────

    def _local_get(self, key: str) -> Optional[bytes]:
        with self._lock:
            item = self._local.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                del self._local[key]
                return None
            self._local.move_to_end(key)
            return value

    def _local_set(self, key: str, value: bytes, ttl: float) -> None:
        with self._lock:
            self._local[key] = (time.monotonic() + ttl, value)
            self._local.move_to_end(key)
            while len(self._local) > self._local_max:
                self._local.popitem(last=False)

    # ─── Public API ─────────────────────────────────────────

    def get(self, key: str) -> Optional[bytes]:
        value = self._local_get(key)
        if value is not None:
            return value
        client = self.redis
        if client is not None:
            try:
                value = client.get(KEY_PREFIX + key)
            except Exception as exc:
                self._redis_failed(exc)
                return None
            if value is not None:
                ttl = DEFAULT_TTL_SECONDS
                try:
                    remaining = client.ttl(KEY_PREFIX + key)
                    ttl = remaining if remaining and remaining > 0 else ttl
                except Exception:
                    pass
                self._local_set(key, value, ttl)
        return value

    def set(self, key: str, value: bytes, ttl: float = DEFAULT_TTL_SECONDS) -> None:
        self._local_set(key, value, ttl)
        client = self.redis
        if client is not None:
            try:
                client.set(KEY_PREFIX + key, value, ex=max(1, int(ttl)))
            except Exception as exc:
                self._redis_failed(exc)

    def get_or_build(self, key: str, build: Callable[[], bytes], ttl: float = DEFAULT_TTL_SECONDS) -> bytes:
        value = self.get(key)
        if value is not None:
            self.hits += 1
            return value
        self.misses += 1
        value = build()
        self.set(key, value, ttl)
        return value

    def clear_local(self) -> None:
        with self._lock:
            self._local.clear()

    def stats(self) -> dict:
        return {"backend": self.backend, "entries": len(self._local), "hits": self.hits, "misses": self.misses}


def cached_json_response(
    request: Request,
    cache: ResponseCache,
    key: str,
    build: Callable[[], object],
    ttl: float = DEFAULT_TTL_SECONDS,
    max_age: int = 60,
) -> Response:
    """
    Serve a JSON body from cache (building it on a miss) with an ETag, and
    answer 304 Not Modified when the client already has this exact body -
    the frontend polls every 30 s, and most polls then cost almost nothing.

    `build` returns a pydantic model (or anything with model_dump_json) or
    raw bytes. It may raise HTTPException; errors are never cached.
    """

    def _serialize() -> bytes:
        body = build()
        if isinstance(body, bytes):
            return body
        return body.model_dump_json().encode()

    body = cache.get_or_build(key, _serialize, ttl)
    etag = '"' + hashlib.blake2b(body, digest_size=12).hexdigest() + '"'
    headers = {"ETag": etag, "Cache-Control": f"public, max-age={max_age}, stale-while-revalidate=300"}
    if etag in [tag.strip() for tag in request.headers.get("if-none-match", "").split(",")]:
        return Response(status_code=304, headers=headers)
    return Response(content=body, media_type="application/json", headers=headers)
