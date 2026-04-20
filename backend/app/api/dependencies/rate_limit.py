"""
Rate limiting for sensitive endpoints (login, refresh, password-reset) — per IP.
"""

from fastapi import Depends, Request

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.exceptions.infrastructure import RateLimitExceeded
from app.domain.users.model import User
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


async def rate_limit_chat(
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Dependency: limits chat messages per user.
    Max 30 messages per minute. Fail open if Redis unavailable.
    """
    key = f"ratelimit:chat:{current_user.user_id}"
    try:
        allowed = await redis_client.rate_limit_check(
            key,
            window_seconds=60,
            max_count=30,
        )
        if not allowed:
            raise RateLimitExceeded(retry_after=60)
    except RateLimitExceeded:
        raise
    except Exception:
        pass  # fail open
