"""Add billing: payments table + premium columns on users.

Revision ID: 013_add_billing
Revises: 012_add_missing_indexes
Create Date: 2026-04-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "013_add_billing"
down_revision = "012_add_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    payment_status_enum = sa.Enum(
        "pending",
        "succeeded",
        "failed",
        "canceled",
        name="payment_status_enum",
    )
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    # 1. Add billing columns to users
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("is_premium", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("users", sa.Column("premium_since", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_users_stripe_customer_id", "users", ["stripe_customer_id"])
    op.create_index("idx_users_is_premium", "users", ["is_premium"])

    # 2. Create payments table
    op.create_table(
        "payments",
        sa.Column("payment_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.String(255), unique=True, nullable=True),
        sa.Column("stripe_session_id", sa.String(255), unique=True, nullable=True),
        sa.Column("stripe_event_id", sa.String(255), unique=True, nullable=True),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="ils"),
        sa.Column("status", payment_status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_payments_user_id", "payments", ["user_id"])
    op.create_index("idx_payments_status", "payments", ["status"])


def downgrade() -> None:
    op.drop_index("idx_payments_status", table_name="payments")
    op.drop_index("idx_payments_user_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("idx_users_is_premium", table_name="users")
    op.drop_index("idx_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "premium_since")
    op.drop_column("users", "is_premium")
    op.drop_column("users", "stripe_customer_id")
    sa.Enum(name="payment_status_enum").drop(op.get_bind(), checkfirst=True)
