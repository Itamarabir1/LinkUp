"""Add missing indexes (align DB with models; 001 did not create them).

Revision ID: 004_add_missing_indexes
Revises: 003_groups_avatar_desc
Create Date: 2025-03-09

Run: alembic upgrade head
"""
from alembic import op


revision = "004_add_missing_indexes"
down_revision = "003_groups_avatar_desc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # rides
    op.create_index("idx_rides_driver_id", "rides", ["driver_id"], unique=False)
    op.create_index("idx_rides_group_id", "rides", ["group_id"], unique=False)
    op.create_index("idx_rides_status", "rides", ["status"], unique=False)
    op.create_index(
        "idx_ride_time_status", "rides", ["departure_time", "status"], unique=False
    )

    # bookings
    op.create_index("idx_bookings_ride", "bookings", ["ride_id"], unique=False)
    op.create_index("idx_bookings_passenger", "bookings", ["passenger_id"], unique=False)
    op.create_index("idx_bookings_status", "bookings", ["status"], unique=False)

    # group_members
    op.create_index(
        "idx_group_members_group_id", "group_members", ["group_id"], unique=False
    )
    op.create_index(
        "idx_group_members_user_id", "group_members", ["user_id"], unique=False
    )

    # passenger_requests
    op.create_index(
        "idx_passenger_requests_passenger_id",
        "passenger_requests",
        ["passenger_id"],
        unique=False,
    )


def downgrade() -> None:
    # passenger_requests
    op.drop_index(
        "idx_passenger_requests_passenger_id",
        table_name="passenger_requests",
    )

    # group_members
    op.drop_index("idx_group_members_user_id", table_name="group_members")
    op.drop_index("idx_group_members_group_id", table_name="group_members")

    # bookings
    op.drop_index("idx_bookings_status", table_name="bookings")
    op.drop_index("idx_bookings_passenger", table_name="bookings")
    op.drop_index("idx_bookings_ride", table_name="bookings")

    # rides
    op.drop_index("idx_ride_time_status", table_name="rides")
    op.drop_index("idx_rides_status", table_name="rides")
    op.drop_index("idx_rides_group_id", table_name="rides")
    op.drop_index("idx_rides_driver_id", table_name="rides")
