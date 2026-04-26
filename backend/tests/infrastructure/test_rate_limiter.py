"""Tests for the atomic Redis rate limiters.

The Lua scripts run inside Redis — we don't unit-test Lua directly. Instead:

* We patch the redis-py ``Script`` callable to a Python translation of each
  Lua script. The translation is line-for-line equivalent (kept in sync
  manually) and lets us deterministically exercise:

  - boundary correctness (no double-burst on sliding window)
  - smooth refill on token bucket
  - concurrent contention (atomicity is asserted via the simulator's
    sequential execution under an asyncio.Lock — same guarantee Redis gives)

* Fail-open paths and result coercion are tested with raising/empty mocks.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any
from unittest.mock import patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.infrastructure.rate_limiter import (
    RateLimiter,
    RateLimitResult,
)


# ---------------------------------------------------------------------------
# Pure-Python translations of the Lua scripts (kept in sync intentionally).
# ---------------------------------------------------------------------------


class FakeTokenBucket:
    """Mirror of token_bucket.lua semantics, in-process."""

    def __init__(self) -> None:
        self._state: dict[str, dict[str, float]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, *, keys: list[str], args: list[Any]) -> list[int]:
        async with self._lock:
            return self._eval(keys[0], args)

    def _eval(self, key: str, args: list[Any]) -> list[int]:
        capacity = float(args[0])
        refill = float(args[1])
        now = float(args[2])
        requested = float(args[3] if len(args) > 3 else 1)

        s = self._state.get(key)
        if s is None:
            tokens = capacity
            ts = now
        else:
            tokens = s["tokens"]
            ts = s["ts"]

        elapsed = max(0.0, now - ts) / 1000.0
        tokens = min(capacity, tokens + elapsed * refill)

        allowed = 0
        retry_after_ms = 0
        if tokens >= requested:
            tokens -= requested
            allowed = 1
        else:
            retry_after_ms = math.ceil(((requested - tokens) / refill) * 1000)

        self._state[key] = {"tokens": tokens, "ts": now}
        return [allowed, int(capacity), int(math.floor(tokens)), int(retry_after_ms)]


class FakeSlidingWindow:
    """Mirror of sliding_window.lua semantics, in-process."""

    def __init__(self) -> None:
        # key -> list[(score, member)] sorted by score
        self._zsets: dict[str, list[tuple[float, str]]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, *, keys: list[str], args: list[Any]) -> list[int]:
        async with self._lock:
            return self._eval(keys[0], args)

    def _eval(self, key: str, args: list[Any]) -> list[int]:
        win = float(args[0])
        maxn = int(args[1])
        now = float(args[2])
        member = str(args[3])

        z = self._zsets.setdefault(key, [])
        z[:] = [e for e in z if e[0] > now - win]

        count = len(z)
        allowed = 0
        retry_after_ms = 0

        if count < maxn:
            z.append((now, member))
            z.sort(key=lambda e: e[0])
            allowed = 1
            count += 1
        else:
            oldest_score = z[0][0]
            retry_after_ms = max(0, int(oldest_score + win - now))

        return [allowed, maxn, max(0, maxn - count), retry_after_ms]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _build_limiter(tb: FakeTokenBucket, sw: FakeSlidingWindow) -> RateLimiter:
    """Wire a RateLimiter whose registered scripts are our fakes."""

    class _FakeRedisClient:
        def register_script(self, lua_text: str) -> Any:
            if "ZREMRANGEBYSCORE" in lua_text:
                return sw
            return tb

    limiter = RateLimiter(client_provider=lambda: _FakeRedisClient())
    return limiter


# ---------------------------------------------------------------------------
# Token bucket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_bucket_allows_capacity_then_blocks():
    """Drain the full bucket → next request is rejected with retry_after_ms."""
    tb, sw = FakeTokenBucket(), FakeSlidingWindow()
    limiter = _build_limiter(tb, sw)
    # Force a fixed clock so all calls are at "the same instant".
    with patch("app.infrastructure.rate_limiter._now_ms", return_value=10_000):
        results: list[RateLimitResult] = []
        for _ in range(5):
            results.append(await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0))

    allowed_flags = [r.allowed for r in results]
    assert allowed_flags == [True, True, True, False, False]
    assert results[0].limit == 3
    assert results[0].remaining == 2
    assert results[3].retry_after_ms > 0


@pytest.mark.asyncio
async def test_token_bucket_refills_over_time():
    """After draining, advance clock 2s with refill_per_sec=1 → 2 fresh tokens."""
    tb, sw = FakeTokenBucket(), FakeSlidingWindow()
    limiter = _build_limiter(tb, sw)
    with patch("app.infrastructure.rate_limiter._now_ms", return_value=10_000):
        for _ in range(3):
            await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0)
        rejected = await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0)
    assert rejected.allowed is False

    # Advance 2 seconds.
    with patch("app.infrastructure.rate_limiter._now_ms", return_value=12_000):
        a = await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0)
        b = await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0)
        c = await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0)
    assert (a.allowed, b.allowed, c.allowed) == (True, True, False)


# ---------------------------------------------------------------------------
# Sliding window — the smoking gun the user identified
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sliding_window_no_burst_at_boundary():
    """Fixed-window has 2x burst at boundary; sliding window does not.

    Fire `max_count` at t=0, attempt one more at t=window_seconds-1 → must
    be rejected because the rolling window still contains the original burst.
    """
    tb, sw = FakeTokenBucket(), FakeSlidingWindow()
    limiter = _build_limiter(tb, sw)

    with patch("app.infrastructure.rate_limiter._now_ms", return_value=0):
        for _ in range(3):
            r = await limiter.sliding_window("k", window_seconds=10, max_count=3)
            assert r.allowed is True

    # Inside the window: must reject.
    with patch("app.infrastructure.rate_limiter._now_ms", return_value=9_999):
        r = await limiter.sliding_window("k", window_seconds=10, max_count=3)
    assert r.allowed is False
    assert r.retry_after_ms > 0
    assert r.retry_after_seconds >= 1

    # After the window slid: must allow.
    with patch("app.infrastructure.rate_limiter._now_ms", return_value=11_000):
        r = await limiter.sliding_window("k", window_seconds=10, max_count=3)
    assert r.allowed is True


@pytest.mark.asyncio
async def test_sliding_window_remaining_decrements():
    """`remaining` decrements with each allowed call inside the window."""
    tb, sw = FakeTokenBucket(), FakeSlidingWindow()
    limiter = _build_limiter(tb, sw)

    with patch("app.infrastructure.rate_limiter._now_ms", return_value=0):
        r1 = await limiter.sliding_window("k", window_seconds=10, max_count=3)
        r2 = await limiter.sliding_window("k", window_seconds=10, max_count=3)
        r3 = await limiter.sliding_window("k", window_seconds=10, max_count=3)

    assert r1.remaining == 2
    assert r2.remaining == 1
    assert r3.remaining == 0


# ---------------------------------------------------------------------------
# Concurrency — atomicity guarantee
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_bucket_concurrent_requests_respect_capacity():
    """50 concurrent requests, capacity=10 → exactly 10 allowed."""
    tb, sw = FakeTokenBucket(), FakeSlidingWindow()
    limiter = _build_limiter(tb, sw)

    with patch("app.infrastructure.rate_limiter._now_ms", return_value=10_000):
        coros = [limiter.token_bucket("k", capacity=10, refill_per_sec=1.0) for _ in range(50)]
        results = await asyncio.gather(*coros)

    allowed = sum(1 for r in results if r.allowed)
    assert allowed == 10


# ---------------------------------------------------------------------------
# Fail-open
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fail_open_when_provider_returns_none():
    """No client (Redis not connected) → allowed=True with full bucket."""
    limiter = RateLimiter(client_provider=lambda: None)
    r = await limiter.token_bucket("k", capacity=5, refill_per_sec=1.0, endpoint="chat")
    assert r.allowed is True
    assert r.remaining == 5
    assert r.limit == 5


@pytest.mark.asyncio
async def test_fail_open_on_redis_error():
    """RedisError during script execution → allowed=True (fail open)."""

    class _RaisingScript:
        async def __call__(self, **_: Any) -> Any:
            raise RedisConnectionError("simulated outage")

    class _Client:
        def register_script(self, _lua: str) -> Any:
            return _RaisingScript()

    limiter = RateLimiter(client_provider=lambda: _Client())
    r = await limiter.sliding_window("k", window_seconds=60, max_count=10, endpoint="auth")
    assert r.allowed is True
    assert r.limit == 10


@pytest.mark.asyncio
async def test_fail_open_when_register_script_raises():
    """register_script itself blowing up → fail open."""

    class _Client:
        def register_script(self, _lua: str) -> Any:
            raise RedisConnectionError("can't talk to redis")

    limiter = RateLimiter(client_provider=lambda: _Client())
    r = await limiter.token_bucket("k", capacity=3, refill_per_sec=1.0)
    assert r.allowed is True


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------


def test_retry_after_seconds_rounding():
    """retry_after_ms always rounds up to seconds, minimum 1 when rejected."""
    assert RateLimitResult(allowed=False, limit=1, remaining=0, retry_after_ms=1).retry_after_seconds == 1
    assert RateLimitResult(allowed=False, limit=1, remaining=0, retry_after_ms=999).retry_after_seconds == 1
    assert RateLimitResult(allowed=False, limit=1, remaining=0, retry_after_ms=1001).retry_after_seconds == 2
    # Allowed → 0
    assert RateLimitResult(allowed=True, limit=1, remaining=1, retry_after_ms=0).retry_after_seconds == 0
