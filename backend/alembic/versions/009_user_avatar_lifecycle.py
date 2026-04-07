"""
009_user_avatar_lifecycle

Add user avatar lifecycle columns to avoid staging/final race:
- avatar_staging_key: temporary staging object key.
- avatar_status: none|processing|ready|failed.

Revision ID: 009_user_avatar_lifecycle
Revises: 008_scheduled_notifications
"""
from alembic import op
import sqlalchemy as sa

revision = "009_user_avatar_lifecycle"
down_revision = "008_scheduled_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'avatar_staging_key'
            ) THEN
                ALTER TABLE users ADD COLUMN avatar_staging_key VARCHAR(255);
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'avatar_status'
            ) THEN
                ALTER TABLE users ADD COLUMN avatar_status VARCHAR(20) NOT NULL DEFAULT 'none';
            END IF;
        END $$;
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'avatar_status'
            ) THEN
                ALTER TABLE users DROP COLUMN avatar_status;
            END IF;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'avatar_staging_key'
            ) THEN
                ALTER TABLE users DROP COLUMN avatar_staging_key;
            END IF;
        END $$;
    """))
