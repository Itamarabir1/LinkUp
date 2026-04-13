"""HTTP-level rate limit: login dependency + 429 + Retry-After."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.db.models  # noqa: F401
from app.db.session import get_db
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
    monkeypatch: pytest.MonkeyPatch,
):
    """429 after exceeding limit; body includes retry hint / Retry-After."""
    call_count = 0

    async def mock_rate_limit(key, window_seconds, max_count):
        nonlocal call_count
        call_count += 1
        return call_count <= 1

    monkeypatch.setattr(
        "app.infrastructure.redis.client.redis_client.rate_limit_check",
        mock_rate_limit,
    )

    body = {"email": "nobody@example.com", "password": "wrongpassword"}

    r1 = await auth_rate_limit_client.post("/api/v1/auth/login", json=body)
    assert r1.status_code != 429

    r2 = await auth_rate_limit_client.post("/api/v1/auth/login", json=body)
    assert r2.status_code == 429
    assert r2.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
    assert "retry_after" in (r2.json().get("details") or {})
    assert r2.headers.get("Retry-After") is not None
