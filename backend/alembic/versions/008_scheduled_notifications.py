"""
008_scheduled_notifications

מה עושה:
  1. יוצר טבלת scheduled_notifications — מחליפה את reminder_sent flag.
  2. מוסיף index חכם על deliver_at WHERE sent_at IS NULL (רק רשומות שטרם נשלחו).
  3. מוחק עמודת reminder_sent מ-rides ו-bookings.

למה:
  reminder_sent היה coupling שגוי — שדה תשתית של notifications בתוך domain model עסקי.
  scheduled_notifications מאפשרת סריקה יעילה (index קטן) ותמיכה בסוגי תזכורות מרובים.

Revision ID: 008_scheduled_notifications
Revises: 007_last_active_at
"""
from alembic import op
import sqlalchemy as sa

revision = "008_scheduled_notifications"
down_revision = "007_last_active_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS scheduled_notifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ride_id UUID REFERENCES rides(ride_id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            type VARCHAR(50) NOT NULL,
            deliver_at TIMESTAMP WITH TIME ZONE NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
    """))

    conn.execute(sa.text("""
        CREATE INDEX IF NOT EXISTS idx_scheduled_notifications_deliver
        ON scheduled_notifications (deliver_at)
        WHERE sent_at IS NULL
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'rides' AND column_name = 'reminder_sent'
            ) THEN
                ALTER TABLE rides DROP COLUMN reminder_sent;
            END IF;
        END $$
    """))

    conn.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'bookings' AND column_name = 'reminder_sent'
            ) THEN
                ALTER TABLE bookings DROP COLUMN reminder_sent;
            END IF;
        END $$
    """))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'rides' AND column_name = 'reminder_sent'
            ) THEN
                ALTER TABLE rides ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE NOT NULL;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'bookings' AND column_name = 'reminder_sent'
            ) THEN
                ALTER TABLE bookings ADD COLUMN reminder_sent BOOLEAN DEFAULT FALSE NOT NULL;
            END IF;
        END $$
    """))

    conn.execute(sa.text("DROP INDEX IF EXISTS idx_scheduled_notifications_deliver"))
    conn.execute(sa.text("DROP TABLE IF EXISTS scheduled_notifications CASCADE"))
