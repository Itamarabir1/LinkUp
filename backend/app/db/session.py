from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# DATABASE_URL must use postgresql+asyncpg://
# Effective statement_timeout is applied per session via asyncpg server_settings.
# Alembic migration 017 sets a higher role-level ceiling (60s) as defense-in-depth.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={
        "statement_cache_size": 0,
        "server_settings": {
            "statement_timeout": f"{settings.DB_STATEMENT_TIMEOUT_MS}ms",
        },
    },
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)

# async_sessionmaker factory
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# FastAPI dependency (optional pattern)
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
