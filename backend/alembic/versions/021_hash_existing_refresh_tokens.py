"""Invalidate plaintext refresh tokens — tokens will be re-issued on next login.

Revision ID: 021_hash_refresh_tokens
Revises: 020_conv_last_msg_at
Create Date: 2026-05-11
"""

from alembic import op

revision = "021_hash_refresh_tokens"
down_revision = "020_conv_last_msg_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing tokens are plaintext JWTs — cannot be hashed retroactively
    # without a coordinated deploy. Null them out; users will re-authenticate
    # and receive a new hashed token.
    op.execute("UPDATE users SET refresh_token = NULL WHERE refresh_token IS NOT NULL")


def downgrade() -> None:
    # Cannot restore plaintext tokens — downgrade is a no-op.
    pass
