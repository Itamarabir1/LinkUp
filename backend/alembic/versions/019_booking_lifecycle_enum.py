"""Add lifecycle values (en_route, arrived, trip_in_progress) to booking_status enum.

Python `BookingStatus` already exposes EN_ROUTE / ARRIVED / TRIP_IN_PROGRESS, and several
queries (e.g. `_DRIVER_ACTIVE_BOOKING_STATUSES`, `_SEAT_RESERVING_BOOKING_STATUSES`) reference
them in `IN (...)` clauses. PostgreSQL rejects unknown enum labels at parameter-bind time even
when no rows match, so this migration is a prerequisite for those code paths.

Revision ID: 019_booking_lifecycle_enum
Revises: 018_rides_composite_indexes
Create Date: 2026-05-06
"""

from alembic import op


revision = "019_booking_lifecycle_enum"
down_revision = "018_rides_composite_indexes"
branch_labels = None
depends_on = None


_NEW_VALUES = ("en_route", "arrived", "trip_in_progress")


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = '{value}'
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'booking_status')
                ) THEN
                    ALTER TYPE booking_status ADD VALUE '{value}';
                END IF;
            END $$
            """,
        )


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum without recreating the type.
    pass
