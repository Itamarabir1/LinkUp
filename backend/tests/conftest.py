"""
Fixtures for async tests.

המודלים משתמשים ב-PostGIS (Geography) — SQLite in-memory לא יכול להריץ Base.metadata.create_all.
טסטים שדורשים DB אמיתי (bookings) רצים רק אם מוגדר:

    TEST_DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME

מומלץ DB ייעודי לבדיקות (לא אותו DB כמו פיתוח), עם סכמה מעודכנת (alembic upgrade head).
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _require_test_db_url() -> str:
    url = (os.environ.get("TEST_DATABASE_URL") or "").strip()
    if not url:
        # ברירת מחדל — ה-DB שרץ ב-docker-compose
        url = "postgresql+asyncpg://admin:password123@localhost:5432/linkup_app"
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
    engine = create_async_engine(test_db_url, echo=False, pool_pre_ping=True)
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
    engine = create_async_engine(url, echo=False, pool_pre_ping=True)
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
