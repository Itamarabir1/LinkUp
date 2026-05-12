"""add CHECK constraints on numeric columns in rides and bookings.

Guards domain invariants at the DB level so no code path — ORM, raw SQL,
migration, or manual fix — can insert nonsensical values.

Revision ID: 024_add_check_constraints
Revises: 023_notification_reads
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision = "024_add_check_constraints"
down_revision = "023_notification_reads"
branch_labels = None
depends_on = None

CONSTRAINTS: list[tuple[str, str, str]] = [
    ("rides", "ck_rides_available_seats_positive", "available_seats >= 1"),
    ("rides", "ck_rides_price_non_negative", "price >= 0"),
    ("rides", "ck_rides_distance_km_non_negative", "distance_km >= 0"),
    ("rides", "ck_rides_duration_min_non_negative", "duration_min >= 0"),
    ("bookings", "ck_bookings_num_seats_positive", "num_seats >= 1"),
]


def upgrade() -> None:
    for table, name, expr in CONSTRAINTS:
        op.create_check_constraint(name, table, sa.text(expr))


def downgrade() -> None:
    for table, name, _expr in reversed(CONSTRAINTS):
        op.drop_constraint(name, table, type_="check")
