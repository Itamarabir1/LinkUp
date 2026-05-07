"""Composite btree indexes on rides for driver/group list queries; drop redundant singleton indexes.

Adds (driver_id, departure_time DESC) and partial (group_id, departure_time DESC) WHERE group_id IS NOT NULL.
Removes idx_rides_driver_id and idx_rides_group_id (superseded by left-prefix composite / filtered index).

Revision ID: 018_rides_composite_indexes
Revises: 017_set_statement_timeout
Create Date: 2026-05-06
"""

import sqlalchemy as sa
from alembic import op

revision = "018_rides_composite_indexes"
down_revision = "017_set_statement_timeout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_rides_driver_departure "
            "ON rides (driver_id, departure_time DESC)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS idx_rides_group_departure "
            "ON rides (group_id, departure_time DESC) WHERE group_id IS NOT NULL"
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_rides_driver_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_rides_group_id"))


def downgrade() -> None:
    op.execute(
        sa.text("CREATE INDEX IF NOT EXISTS idx_rides_driver_id ON rides (driver_id)")
    )
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_rides_group_id ON rides (group_id)"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_rides_driver_departure"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_rides_group_departure"))
