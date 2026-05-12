import os
import sys
import asyncio
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.base import Base

import app.db.models  # register all models in metadata before autogenerate


def _resolve_database_url() -> str:
    """Resolve DATABASE_URL for migrations without instantiating full app Settings.

    Migrations are a schema-only concern and must not depend on application
    runtime secrets (SECRET_KEY, Firebase, Stripe, etc.).

    Priority:
      1. ``DATABASE_URL`` env var (CI, managed databases, production).
      2. Compose from individual ``POSTGRES_*`` env vars (local dev ``.env``).

    URL normalisation mirrors ``Settings.DATABASE_URL`` (asyncpg driver).
    """
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url

    user = os.environ.get("POSTGRES_USER", "")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


config = context.config

config.set_main_option("sqlalchemy.url", _resolve_database_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
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
    
    configuration = config.get_section(config.config_ini_section, {})
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
