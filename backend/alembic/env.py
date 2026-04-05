import os
import sys
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config
# 1. הוספת נתיב הפרויקט
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# 2. ייבוא ה-settings וה-Base
from app.core.config import settings
from app.db.base import Base

import app.db.models  # רישום כל המודלים ב-metadata לפני autogenerate

# --- ייבוא מודלים לרישום ב-Metadata ---

config = context.config

# 3. חיבור ה-URL מה-settings ל-Alembic
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# עכשיו ה-target_metadata מכיל את כל המודלים שייבאנו למעלה
target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    # התעלמות מטבלאות מערכת של PostGIS
    ignored_prefixes = ["tiger", "topology", "spatial_ref_sys", "geography_columns", "geometry_columns"]
    if type_ == "table":
        for prefix in ignored_prefixes:
            if name.startswith(prefix) or name in ignored_prefixes:
                return False
    return True

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "pyformat"},
        include_object=include_object  # הוספתי גם כאן ליתר ביטחון
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an Async Engine."""
    
    # יצירת קונפיגורציה שמתאימה לדרייבר אסינכרוני
    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # כאן הקסם: מריצים פונקציה סינכרונית בתוך הקשר אסינכרוני
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    # הרצה של הלופ האסינכרוני
    asyncio.run(run_migrations_online())