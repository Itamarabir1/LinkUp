from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Awaitable, Callable, TypeVar

from app.infrastructure.metrics import (
    cache_fail_open_total,
    cache_lock_acquired_total,
    cache_stampede_avoided_total,
)
from app.infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)

T = TypeVar("T")

_UNLOCK_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


async def _release_lock(lock_key: str, token: str) -> None:
    try:
        if redis_client.client is None:
            return
        await redis_client.client.eval(_UNLOCK_SCRIPT, 1, lock_key, token)
    except Exception as exc:
        logger.debug("Cache lock release failed key=%s: %s", lock_key, exc)


async def get_or_compute(
    key: str,
    fetcher: Callable[[], Awaitable[T | None]],
    ttl: int,
    *,
    key_prefix: str = "generic",
    lock_ttl: int = 10,
    lock_timeout: float = 5.0,
    poll_interval: float = 0.05,
) -> T | None:
    """
    Stampede protection for read-through cache using Redis mutex.

    Flow:
    1) Attempt cache read.
    2) On miss, acquire distributed lock (SET NX EX).
    3) Leader computes and stores result; followers poll cache with bounded timeout.
    4) Fail open: any Redis/lock issue falls back to direct fetcher execution.
    """
    lock_key = f"{key}:lock"

    try:
        cached = await redis_client.get(key)
        if cached is not None:
            return cached

        if redis_client.client is None:
            await redis_client.connect()

        token = uuid.uuid4().hex
        lock_ttl = max(1, int(lock_ttl))
        won = await redis_client.client.set(lock_key, token, ex=lock_ttl, nx=True)

        if won:
            cache_lock_acquired_total.labels(key_prefix=key_prefix).inc()
            try:
                # Double-check after acquiring lock in case another process won and filled previously.
                cached_after_lock = await redis_client.get(key)
                if cached_after_lock is not None:
                    return cached_after_lock

                value = await fetcher()
                if value is not None:
                    await redis_client.save(key, value, expire=ttl)
                return value
            finally:
                await _release_lock(lock_key, token)

        deadline = asyncio.get_running_loop().time() + max(0.0, lock_timeout)
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(max(0.01, poll_interval))
            polled = await redis_client.get(key)
            if polled is not None:
                cache_stampede_avoided_total.labels(key_prefix=key_prefix).inc()
                return polled

        # Follower timeout: fail-open compute (best effort write-through).
        value = await fetcher()
        if value is not None:
            try:
                await redis_client.save(key, value, expire=ttl)
            except Exception:
                pass
        return value

    except Exception as exc:
        cache_fail_open_total.labels(key_prefix=key_prefix).inc()
        logger.warning("Cache stampede helper fail-open for key=%s: %s", key, exc)
        return await fetcher()
