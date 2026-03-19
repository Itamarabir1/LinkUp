from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# וודא ש-DATABASE_URL מתחיל ב-postgresql+asyncpg://
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,  # ניהול נכון של מאגר חיבורים
    max_overflow=20,
    pool_pre_ping=True,  # מונע חיבורים מתים (PostgreSQL סוגר חיבורים לא פעילים)
)

# שימוש ב-async_sessionmaker לרמה של סניור
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Dependency ל-FastAPI (אם צריך)
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
