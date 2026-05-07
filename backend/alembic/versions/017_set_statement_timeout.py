"""Defensive Postgres statement_timeout ceiling for the application role.

Sets a fixed 60000ms ceiling at the role level via ALTER ROLE CURRENT_USER SET.
This is a *defensive cap* (gate of last resort), not the operational value:
the effective per-session timeout is set by the application via SQLAlchemy
`connect_args` -> asyncpg `server_settings` (driven by `DB_STATEMENT_TIMEOUT_MS`
in `app/db/session.py`). Keeping the migration value as a hard literal makes
schema state deterministic regardless of which environment runs `alembic upgrade`.

Revision ID: 017_set_statement_timeout
Revises: 016_merge015_heads
Create Date: 2026-05-06
"""

from alembic import op

revision = "017_set_statement_timeout"
down_revision = "016_merge015_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER ROLE CURRENT_USER SET statement_timeout = '60000ms'")


def downgrade() -> None:
    op.execute("ALTER ROLE CURRENT_USER RESET statement_timeout")
