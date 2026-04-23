"""Reconcile billing schema after partial migration states.

Revision ID: 014_fix_billing_partial_state
Revises: 013_add_billing
Create Date: 2026-04-23
"""

from alembic import op

revision = "014_fix_billing_partial_state"
down_revision = "013_add_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Ensure enum exists (idempotent, safe on duplicate)
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE payment_status_enum AS ENUM ('pending', 'succeeded', 'failed', 'canceled');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END
        $$;
        """
    )

    # 2) Ensure users billing columns + indexes exist
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255);")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_premium BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_since TIMESTAMPTZ;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users (stripe_customer_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_is_premium ON users (is_premium);")

    # 3) Ensure payments table exists
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payments (
            payment_id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            stripe_payment_intent_id VARCHAR(255) UNIQUE,
            stripe_session_id VARCHAR(255) UNIQUE,
            stripe_event_id VARCHAR(255) UNIQUE,
            amount NUMERIC(10,2) NOT NULL,
            currency VARCHAR(10) NOT NULL DEFAULT 'ils',
            status payment_status_enum NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        """
    )

    # 4) Reconcile existing partial payments table (if columns/types were drifted)
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(255);")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS stripe_session_id VARCHAR(255);")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS stripe_event_id VARCHAR(255);")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS currency VARCHAR(10) NOT NULL DEFAULT 'ils';")
    op.execute("ALTER TABLE payments ADD COLUMN IF NOT EXISTS status payment_status_enum;")
    op.execute("ALTER TABLE payments ALTER COLUMN status SET DEFAULT 'pending';")
    op.execute("ALTER TABLE payments ALTER COLUMN status SET NOT NULL;")

    # 5) Ensure indexes exist
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (status);")


def downgrade() -> None:
    # Forward-only reconciliation migration: intentionally no destructive downgrade.
    pass

