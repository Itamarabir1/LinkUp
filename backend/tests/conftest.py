"""
Fixtures for async tests.

המודלים משתמשים ב-PostGIS (Geography) — SQLite in-memory לא יכול להריץ Base.metadata.create_all.
טסטים שדורשים DB אמיתי (bookings) רצים רק אם מוגדר:

    DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME
    (או TEST_DATABASE_URL לתאימות לאחור)

מומלץ DB ייעודי לבדיקות (לא אותו DB כמו פיתוח), עם סכמה מעודכנת (alembic upgrade head).

הפרדת סשנים:
- db_session — טרנזקציה אחת; commit ממופה ל-flush ואז rollback (מהיר לשירותים).
- e2e_session_factory — סשן לכל שימוש בלי monkeypatch; מתאים ל-HTTP עם commit אמיתי בין בקשות.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncGenerator

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.api.dependencies.admin import get_current_admin_user
from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.domain.rides.enum import RideStatus
from app.main import app
from tests.helpers.db_factories import make_ride, make_user


def _require_test_db_url() -> str:
    url = (os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL") or "").strip()
    if not url:
        # ברירת מחדל — ה-DB שרץ ב-docker-compose
        url = "postgresql+asyncpg://admin:password123@127.0.0.1:5432/linkup_app"
    return url


@pytest.fixture(scope="session")
def test_db_url() -> str:
    return _require_test_db_url()


@pytest_asyncio.fixture
async def e2e_session_factory(test_db_url: str):
    """
    Session factory without commit monkeypatch.
    Useful for API-like flows where each request should see real commit boundaries.
    """
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"ssl": False},
    )
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(monkeypatch: pytest.MonkeyPatch):
    """
    חיבור PostgreSQL עם טרנזקציה אחת: commit ב-service מוחלף ב-flush כדי לאשר rollback בסוף.
    """
    url = _require_test_db_url()
    engine = create_async_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args={"ssl": False},
    )
    async with engine.connect() as conn:
        trans = await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
        async with session_factory() as session:

            async def commit_as_flush() -> None:
                await session.flush()

            monkeypatch.setattr(session, "commit", commit_as_flush)
            yield session
        await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client_no_auth(
    e2e_session_factory: async_sessionmaker,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client without auth (for 401 tests)."""

    async def _get_db_override():
        async with e2e_session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield client
        finally:
            app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_users_and_ride(e2e_session_factory: async_sessionmaker):
    async with e2e_session_factory() as s:
        driver = await make_user(s, "api-driver", email_suffix="api")
        passenger = await make_user(s, "api-passenger", email_suffix="api")
        ride = await make_ride(s, driver.user_id, status=RideStatus.OPEN, seats=2)
        await s.commit()
        return {
            "driver": driver,
            "passenger": passenger,
            "ride": ride,
        }


@pytest_asyncio.fixture
async def api_client_with_overrides(
    e2e_session_factory: async_sessionmaker,
) -> AsyncGenerator[tuple[AsyncClient, dict], None]:
    auth_ctx: dict[str, object] = {"user": None}

    async def _get_db_override():
        async with e2e_session_factory() as s:
            yield s

    async def _get_current_user_override():
        user = auth_ctx.get("user")
        if user is None:
            raise RuntimeError("Test auth context missing user")
        return user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override
    app.dependency_overrides[get_current_admin_user] = _get_current_user_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield client, auth_ctx
        finally:
            app.dependency_overrides.clear()
