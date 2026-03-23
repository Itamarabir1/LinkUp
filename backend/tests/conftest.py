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
        pytest.skip(
            "Set TEST_DATABASE_URL to postgresql+asyncpg://... for DB integration tests "
            "(models use PostGIS Geography — SQLite :memory: is not supported)."
        )
    return url


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
