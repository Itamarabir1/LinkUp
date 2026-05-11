"""Add composite / partial indexes for hot CRUD queries.

Revision ID: 022_add_missing_indexes
Revises: 021_hash_refresh_tokens
Create Date: 2026-05-11
"""

import sqlalchemy as sa
from alembic import op

revision = "022_add_missing_indexes"
down_revision = "021_hash_refresh_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bookings(passenger_id, status) — get_passenger_active_bookings filters both
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_bookings_passenger_status "
        "ON bookings (passenger_id, status)"
    ))

    # bookings(ride_id, status) — get_ride_bookings_by_status_async filters both
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_bookings_ride_status "
        "ON bookings (ride_id, status)"
    ))

    # passenger_requests(status) — search queries filter by status
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_passenger_requests_status "
        "ON passenger_requests (status)"
    ))

    # passenger_requests(passenger_id, status) — get_my_requests filters both
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_passenger_requests_passenger_status "
        "ON passenger_requests (passenger_id, status)"
    ))

    # outbox_events(status, created_at) — pending events polling
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_outbox_events_status_created "
        "ON outbox_events (status, created_at) WHERE status = 'PENDING'"
    ))

    # users(last_active_at) — presence queries
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS idx_users_last_active_at "
        "ON users (last_active_at DESC) WHERE last_active_at IS NOT NULL"
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS idx_users_last_active_at"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_outbox_events_status_created"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_passenger_requests_passenger_status"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_passenger_requests_status"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_bookings_ride_status"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_bookings_passenger_status"))
