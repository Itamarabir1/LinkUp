"""Add conversation_participants (last_read_at per user) with backfill.

Revision ID: 006_chat_participants
Revises: 005_add_active_ride_status
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa


revision = "006_chat_participants"
down_revision = "005_add_active_ride_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_participants",
        sa.Column(
            "conversation_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_conversation_participants_user_last_read",
        "conversation_participants",
        ["user_id", "last_read_at"],
    )

    # Backfill from existing 1:1 conversations table.
    # joined_at seeded from conversations.created_at; last_read_at stays NULL (unread computed vs joined_at/NULL).
    op.execute(
        """
        INSERT INTO conversation_participants (conversation_id, user_id, joined_at, last_read_at)
        SELECT c.conversation_id, c.user_id_1, c.created_at, NULL
        FROM conversations c
        ON CONFLICT (conversation_id, user_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO conversation_participants (conversation_id, user_id, joined_at, last_read_at)
        SELECT c.conversation_id, c.user_id_2, c.created_at, NULL
        FROM conversations c
        ON CONFLICT (conversation_id, user_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_participants_user_last_read", table_name="conversation_participants")
    op.drop_table("conversation_participants")

