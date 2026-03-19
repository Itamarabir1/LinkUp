"""Add ACTIVE to ride_status enum (GPS tracking: נסיעה בתנועה).

Revision ID: 005_add_active_ride_status
Revises: 004_add_missing_indexes
Create Date: 2025-03-09

Run: alembic upgrade head
"""
from alembic import op


revision = "005_add_active_ride_status"
down_revision = "004_add_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL: ADD VALUE is safe to run multiple times only from PG 10+
    # If the value already exists, the statement will error; use DO block for idempotency
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumlabel = 'active'
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ride_status')
            ) THEN
                ALTER TYPE ride_status ADD VALUE 'active';
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    # PostgreSQL does not support removing a value from an enum without recreating the type
    pass
