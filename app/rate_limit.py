"""Shared rate limiter (slowapi/limits), keyed by client IP.

Kept in its own module so both app/main.py (middleware + exception handler)
and individual routers (the @limiter.limit(...) decorators) can import the
same Limiter instance without a circular import.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
