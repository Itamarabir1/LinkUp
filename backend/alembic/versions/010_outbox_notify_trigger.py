"""
010_outbox_notify_trigger

Add PostgreSQL LISTEN/NOTIFY trigger for outbox inserts.

Revision ID: 010_outbox_notify_trigger
Revises: 009_user_avatar_lifecycle
"""
from alembic import op
import sqlalchemy as sa

revision = "010_outbox_notify_trigger"
down_revision = "009_user_avatar_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION notify_outbox_insert()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                PERFORM pg_notify('outbox_new_event', NEW.id::text);
                RETURN NEW;
            END;
            $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE TRIGGER trg_outbox_notify
            AFTER INSERT ON outbox_events
            FOR EACH ROW EXECUTE FUNCTION notify_outbox_insert();
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TRIGGER IF EXISTS trg_outbox_notify ON outbox_events;"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS notify_outbox_insert();"))
