"""HTTP-level rate limit: login dependency emits 429 + standard headers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.db.models  # noqa: F401
from app.db.session import get_db
from app.infrastructure.rate_limiter import RateLimitResult
from app.main import app


@pytest_asyncio.fixture
async def auth_rate_limit_client(
    e2e_session_factory: async_sessionmaker,
) -> AsyncGenerator[AsyncClient, None]:
    """Reuse same DB setup as other API tests (not env DATABASE_URL only)."""

    async def _get_db_override():
        async with e2e_session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_max_requests(
    auth_rate_limit_client: AsyncClient,
):
    """429 after exceeding limit; standard rate-limit headers are present."""
    call_count = 0

    async def mock_sliding_window(key, *, window_seconds, max_count, endpoint="default"):
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            return RateLimitResult(
                allowed=True,
                limit=max_count,
                remaining=max_count - call_count,
                retry_after_ms=0,
            )
        return RateLimitResult(
            allowed=False,
            limit=max_count,
            remaining=0,
            retry_after_ms=42_000,
        )

    body = {"email": "nobody@example.com", "password": "wrongpassword"}

    with patch(
        "app.infrastructure.rate_limiter.rate_limiter.sliding_window",
        new=AsyncMock(side_effect=mock_sliding_window),
    ):
        r1 = await auth_rate_limit_client.post("/api/v1/auth/login", json=body)
        assert r1.status_code != 429

        r2 = await auth_rate_limit_client.post("/api/v1/auth/login", json=body)

    assert r2.status_code == 429
    body_json = r2.json()
    assert body_json["error_code"] == "RATE_LIMIT_EXCEEDED"
    details = body_json.get("details") or {}
    assert details.get("retry_after") is not None
    assert details.get("limit") is not None
    assert details.get("remaining") == 0

    # Standard rate-limit headers (Stripe / GitHub convention)
    assert r2.headers.get("Retry-After") is not None
    assert r2.headers.get("X-RateLimit-Limit") is not None
    assert r2.headers.get("X-RateLimit-Remaining") == "0"
    assert r2.headers.get("X-RateLimit-Reset") is not None
