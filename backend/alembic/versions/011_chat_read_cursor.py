"""
011_chat_read_cursor

Add last_read_message_id to conversation_participants.
This is a message-based read cursor - more reliable than
deriving read state from timestamps.

Revision ID: 011_chat_read_cursor
Revises: 010_outbox_notify_trigger
"""
from alembic import op
import sqlalchemy as sa

revision = "011_chat_read_cursor"
down_revision = "010_outbox_notify_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'conversation_participants'
                    AND column_name = 'last_read_message_id'
                ) THEN
                    ALTER TABLE conversation_participants
                    ADD COLUMN last_read_message_id BIGINT NULL;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            ALTER TABLE conversation_participants
            DROP COLUMN IF EXISTS last_read_message_id;
            """
        )
    )
