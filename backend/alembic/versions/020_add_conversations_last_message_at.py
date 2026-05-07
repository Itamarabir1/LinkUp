"""Persist chat inbox sort timestamp on conversations.

Adds `conversations.last_message_at` and backfills from the latest message timestamp
per conversation (fallback to conversation `created_at` when no messages exist).
Also adds an index for inbox ordering.

Revision ID: 020_add_conversations_last_message_at
Revises: 019_booking_lifecycle_enum
Create Date: 2026-05-07
"""

import sqlalchemy as sa
from alembic import op

revision = "020_add_conversations_last_message_at"
down_revision = "019_booking_lifecycle_enum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE conversations c
            SET last_message_at = COALESCE(
                (
                    SELECT MAX(m.created_at)
                    FROM messages m
                    WHERE m.conversation_id = c.conversation_id
                ),
                c.created_at
            )
            """,
        )
    )
    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at
            ON conversations (last_message_at DESC NULLS LAST)
            """,
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_conversations_last_message_at"))
    op.drop_column("conversations", "last_message_at")
