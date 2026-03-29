"""
Rate limiting ל-endpoints רגישים (login, refresh, password-reset) – הגבלה לפי IP.
"""

from fastapi import Request

from app.core.config import settings
from app.core.exceptions.infrastructure import RateLimitExceeded
from app.infrastructure.redis.client import redis_client


def _client_ip(request: Request) -> str:
    """מחזיר IP הלקוח – X-Forwarded-For אם מאחורי proxy, אחרת client.host."""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_auth(request: Request) -> None:
    """
    Dependency: מגביל מספר בקשות ל-auth (login, refresh, password-reset) לפי IP.
    אם חורג – 429 Too Many Requests. משתמש ב-Redis; אם Redis לא זמין – מאפשר (fail open).
    """
    ip = _client_ip(request)
    key = f"ratelimit:auth:{ip}"
    window = getattr(settings, "RATE_LIMIT_AUTH_WINDOW_SECONDS", 60)
    max_req = getattr(settings, "RATE_LIMIT_AUTH_MAX_REQUESTS", 10)

    allowed = await redis_client.rate_limit_check(
        key, window_seconds=window, max_count=max_req
    )
    if not allowed:
        raise RateLimitExceeded(retry_after=window)
