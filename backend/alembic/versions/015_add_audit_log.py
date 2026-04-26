"""Add audit_log table for admin and billing actions.

Revision ID: 015_add_audit_log
Revises: 014_fix_billing_partial_state
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "015_add_audit_log"
down_revision = "014_fix_billing_partial_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.execute("CREATE INDEX idx_audit_actor_ts ON audit_log (actor_user_id, created_at DESC)")
    op.create_index("idx_audit_resource", "audit_log", ["resource_type", "resource_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_audit_resource", table_name="audit_log")
    op.drop_index("idx_audit_actor_ts", table_name="audit_log")
    op.drop_table("audit_log")
