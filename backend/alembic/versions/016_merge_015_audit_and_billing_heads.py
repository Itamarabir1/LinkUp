"""Merge alembic heads: audit_log branch and billing idempotency branch.

Revision ID: 016_merge015_heads
Revises: 015_add_audit_log, 015_billing_idempotency_and_indexes
Create Date: 2026-05-01
"""

revision = "016_merge015_heads"
down_revision = (
    "015_add_audit_log",
    "015_billing_idempotency_and_indexes",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
