"""
Rate limiting for sensitive endpoints (login, refresh, password-reset) — per IP.
"""

from fastapi import Request

from app.core.config import settings
from app.core.exceptions.infrastructure import RateLimitExceeded
from app.infrastructure.redis.client import redis_client


def _client_ip(request: Request) -> str:
    """Returns client IP — X-Forwarded-For if behind a proxy, else client.host."""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_auth(request: Request) -> None:
    """
    Dependency: limits auth requests (login, refresh, password-reset) per IP.
    On exceed — 429 Too Many Requests. Uses Redis; if Redis is unavailable — allows (fail open).
    """
    ip = _client_ip(request)
    key = f"ratelimit:auth:{ip}"
    window = getattr(settings, "RATE_LIMIT_AUTH_WINDOW_SECONDS", 60)
    max_req = getattr(settings, "RATE_LIMIT_AUTH_MAX_REQUESTS", 10)

    allowed = await redis_client.rate_limit_check(key, window_seconds=window, max_count=max_req)
    if not allowed:
        raise RateLimitExceeded(retry_after=window)
