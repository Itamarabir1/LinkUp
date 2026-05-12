"""notification_reads — server-side read-state for the notifications feed.

Replaces unbounded localStorage accumulation with a DB-backed read tracker.
Composite PK (user_id, booking_id, created_at) mirrors the existing frontend
notification identity key.

Revision ID: 023_notification_reads
Revises: 022_add_missing_indexes
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision = "023_notification_reads"
down_revision = "022_add_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS notification_reads (
            user_id    UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            booking_id UUID NOT NULL REFERENCES bookings(booking_id) ON DELETE CASCADE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            read_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            PRIMARY KEY (user_id, booking_id, created_at)
        )
    """))

    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_notification_reads_user "
        "ON notification_reads (user_id)"
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_notification_reads_user"))
    op.execute(sa.text("DROP TABLE IF EXISTS notification_reads CASCADE"))
