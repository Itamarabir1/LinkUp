"""Add billing idempotency keys and pending index.

Revision ID: 015_billing_idempotency_and_indexes
Revises: 014_fix_billing_partial_state
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015_billing_idempotency_and_indexes"
down_revision = "014_fix_billing_partial_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_key", sa.String(length=128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "client_key", "endpoint", name="uq_idem_user_client_endpoint"),
    )
    op.create_index("idx_idempotency_expires_at", "idempotency_keys", ["expires_at"], unique=False)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payments_status_created
        ON payments (status, created_at)
        WHERE status = 'pending';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_payments_status_created;")
    op.drop_index("idx_idempotency_expires_at", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
