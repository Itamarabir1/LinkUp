"""Add users.last_active_at for chat activity (distinct from last_login).

Revision ID: 007_last_active_at
Revises: 006_chat_participants
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "007_last_active_at"
down_revision = "006_chat_participants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_users_last_active_at",
        "users",
        ["last_active_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_users_last_active_at", table_name="users")
    op.drop_column("users", "last_active_at")
