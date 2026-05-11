"""HTTP-level rate limit dependencies.

Two algorithms by design (see ``docs/FEATURE_DECISIONS.md``):

* ``rate_limit_auth``    — sliding window log (no burst, anti-bruteforce).
* ``rate_limit_chat``    — token bucket (burst-tolerant API throttle).
* ``rate_limit_rides``   — sliding window log (anti-abuse, per-user ride creation).

All are atomic via Lua, all fail-open if Redis is unavailable.
On rejection a 429 is raised with full ``X-RateLimit-*`` + ``Retry-After``
header metadata surfaced by the central exception handler.
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.exceptions.infrastructure import RateLimitExceeded
from app.domain.users.model import User
from app.infrastructure.metrics import rate_limit_rejected_total
from app.infrastructure.rate_limiter import rate_limiter


def _client_ip(request: Request) -> str:
    """Returns client IP — X-Forwarded-For if behind a proxy, else client.host."""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_auth(request: Request) -> None:
    """Sliding-window limit on auth endpoints (login, refresh, password-reset) per IP.

    Anti-bruteforce: a quiet attacker cannot stockpile a burst — every request
    counts inside a true rolling window.
    """
    ip = _client_ip(request)
    key = f"ratelimit:auth:{ip}"
    result = await rate_limiter.sliding_window(
        key,
        window_seconds=settings.RATE_LIMIT_AUTH_WINDOW_SECONDS,
        max_count=settings.RATE_LIMIT_AUTH_MAX_PER_WINDOW,
        endpoint="auth",
    )
    if not result.allowed:
        rate_limit_rejected_total.labels(algorithm="sliding_window", endpoint="auth").inc()
        raise RateLimitExceeded(
            retry_after=result.retry_after_seconds,
            limit=result.limit,
            remaining=result.remaining,
        )


async def rate_limit_chat(
    current_user: User = Depends(get_current_user),
) -> None:
    """Token-bucket limit on chat per user. Burst tolerated up to capacity, then refills."""
    key = f"ratelimit:chat:{current_user.user_id}"
    result = await rate_limiter.token_bucket(
        key,
        capacity=settings.RATE_LIMIT_CHAT_BUCKET_CAPACITY,
        refill_per_sec=settings.RATE_LIMIT_CHAT_REFILL_PER_SEC,
        endpoint="chat",
    )
    if not result.allowed:
        rate_limit_rejected_total.labels(algorithm="token_bucket", endpoint="chat").inc()
        raise RateLimitExceeded(
            retry_after=result.retry_after_seconds,
            limit=result.limit,
            remaining=result.remaining,
        )


async def rate_limit_rides(
    current_user: User = Depends(get_current_user),
) -> None:
    """Sliding-window limit on ride creation per user. Anti-abuse: max 10 rides per hour."""
    key = f"ratelimit:rides:{current_user.user_id}"
    result = await rate_limiter.sliding_window(
        key,
        window_seconds=settings.RATE_LIMIT_RIDES_WINDOW_SECONDS,
        max_count=settings.RATE_LIMIT_RIDES_MAX_PER_WINDOW,
        endpoint="rides",
    )
    if not result.allowed:
        rate_limit_rejected_total.labels(algorithm="sliding_window", endpoint="rides").inc()
        raise RateLimitExceeded(
            retry_after=result.retry_after_seconds,
            limit=result.limit,
            remaining=result.remaining,
        )
