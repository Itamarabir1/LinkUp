"""Atomic Redis-backed rate limiters.

Two algorithms, one service:

- ``token_bucket`` — burst-tolerant API throttle. Suitable for chat / generic API.
- ``sliding_window`` — strict rolling window with no burst. Suitable for auth
  endpoints (login, refresh, password reset) where burst capacity would let an
  attacker stage 10 silent minutes followed by a 10-attempt second.

Both algorithms are implemented as Lua scripts and registered via
``redis-py``'s ``register_script`` helper, which:

* Caches the script SHA and uses ``EVALSHA`` for subsequent calls.
* Falls back to ``EVAL`` on ``NOSCRIPT`` errors (e.g. after Sentinel
  failover or ``SCRIPT FLUSH``).

Fail-open: any ``RedisError`` / timeout returns ``RateLimitResult(allowed=True, ...)``
and bumps ``rate_limit_redis_errors_total``. The decision: rate limiting is a
defense-in-depth layer; an outage of Redis must not take down login or chat.

Trade-offs (deliberate):

* Wall clock comes from the caller (``now_ms``). N backend instances may have
  small NTP-bounded drift (usually <10ms on EC2 with chrony). Acceptable for
  rate-limit precision; documented in ``docs/FEATURE_DECISIONS.md``.
* Float arithmetic in Lua 5.1 is precise enough for human-scale rate limits
  (seconds-to-minutes). We do not store integer "milli-tokens".
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from redis.exceptions import RedisError

from app.infrastructure.metrics import (
    rate_limit_evaluation_seconds,
    rate_limit_redis_errors_total,
)
from app.infrastructure.redis.lua import SLIDING_WINDOW_LUA, TOKEN_BUCKET_LUA

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    """Outcome of a rate-limit check.

    Attributes:
        allowed: True if the request is granted.
        limit: The configured cap (capacity for token bucket, max_count for
            sliding window). Surfaced as ``X-RateLimit-Limit``.
        remaining: How many requests remain in the current window/bucket.
            Surfaced as ``X-RateLimit-Remaining``.
        retry_after_ms: Milliseconds until the next request should be
            possible. 0 when ``allowed`` is True. Surfaced as ``Retry-After``
            (rounded up to seconds).
    """

    allowed: bool
    limit: int
    remaining: int
    retry_after_ms: int

    @classmethod
    def fail_open(cls, *, limit: int) -> RateLimitResult:
        """Result returned when Redis is unavailable. Permissive by design."""
        return cls(allowed=True, limit=limit, remaining=limit, retry_after_ms=0)

    @property
    def retry_after_seconds(self) -> int:
        """Retry-After header value: ceil to seconds, minimum 1 when rejected."""
        if self.allowed:
            return 0
        return max(1, (self.retry_after_ms + 999) // 1000)


def _now_ms() -> int:
    return int(time.time() * 1000)


class RateLimiter:
    """Stateless service object; owns two registered Lua scripts.

    Wired with a provider callable that yields the underlying ``redis.Redis``
    (or Sentinel master) so the limiter can re-acquire the client after
    reconnects without holding a stale reference.
    """

    def __init__(self, client_provider: Callable[[], Any]):
        self._provider = client_provider
        self._tb_script: Any | None = None
        self._sw_script: Any | None = None

    async def _ensure_loaded(self) -> tuple[Any, Any] | None:
        """Lazy-load both scripts on the current client. Returns (tb, sw) or None on failure."""
        try:
            client = self._provider()
            if client is None:
                return None
            if self._tb_script is None or self._sw_script is None:
                self._tb_script = client.register_script(TOKEN_BUCKET_LUA)
                self._sw_script = client.register_script(SLIDING_WINDOW_LUA)
            return self._tb_script, self._sw_script
        except Exception as exc:
            logger.warning("RateLimiter script load failed: %s", exc)
            return None

    @staticmethod
    def _coerce(raw: Any) -> tuple[int, int, int, int]:
        """Lua arrays come back as Python lists of bytes/str/ints depending on decode."""
        return (
            int(raw[0]),
            int(raw[1]),
            int(raw[2]),
            int(raw[3]),
        )

    async def token_bucket(
        self,
        key: str,
        *,
        capacity: int,
        refill_per_sec: float,
        endpoint: str = "default",
    ) -> RateLimitResult:
        """Token Bucket: burst-tolerant API throttle.

        ``capacity`` requests can be made instantly; refills smoothly at
        ``refill_per_sec`` until the cap. Use for general API + chat.
        """
        loaded = await self._ensure_loaded()
        if loaded is None:
            rate_limit_redis_errors_total.labels(endpoint=endpoint).inc()
            return RateLimitResult.fail_open(limit=capacity)

        tb_script, _ = loaded
        with rate_limit_evaluation_seconds.labels(algorithm="token_bucket").time():
            try:
                raw = await tb_script(
                    keys=[key],
                    args=[capacity, refill_per_sec, _now_ms(), 1],
                )
            except RedisError as exc:
                logger.warning("Rate limit (token_bucket) Redis error key=%s: %s", key, exc)
                rate_limit_redis_errors_total.labels(endpoint=endpoint).inc()
                return RateLimitResult.fail_open(limit=capacity)

        allowed, limit, remaining, retry_after_ms = self._coerce(raw)
        return RateLimitResult(
            allowed=bool(allowed),
            limit=limit,
            remaining=remaining,
            retry_after_ms=retry_after_ms,
        )

    async def sliding_window(
        self,
        key: str,
        *,
        window_seconds: int,
        max_count: int,
        endpoint: str = "default",
    ) -> RateLimitResult:
        """Sliding Window Log: strict, no-burst, anti-bruteforce friendly.

        Up to ``max_count`` requests in any rolling ``window_seconds`` interval.
        Use for auth endpoints.
        """
        loaded = await self._ensure_loaded()
        if loaded is None:
            rate_limit_redis_errors_total.labels(endpoint=endpoint).inc()
            return RateLimitResult.fail_open(limit=max_count)

        _, sw_script = loaded
        member = uuid.uuid4().hex
        with rate_limit_evaluation_seconds.labels(algorithm="sliding_window").time():
            try:
                raw = await sw_script(
                    keys=[key],
                    args=[window_seconds * 1000, max_count, _now_ms(), member],
                )
            except RedisError as exc:
                logger.warning("Rate limit (sliding_window) Redis error key=%s: %s", key, exc)
                rate_limit_redis_errors_total.labels(endpoint=endpoint).inc()
                return RateLimitResult.fail_open(limit=max_count)

        allowed, limit, remaining, retry_after_ms = self._coerce(raw)
        return RateLimitResult(
            allowed=bool(allowed),
            limit=limit,
            remaining=remaining,
            retry_after_ms=retry_after_ms,
        )


def _default_client_provider() -> Any | None:
    """Resolve the shared async Redis client at call time (after .connect())."""
    from app.infrastructure.redis.client import redis_client

    return redis_client.client


rate_limiter = RateLimiter(_default_client_provider)
