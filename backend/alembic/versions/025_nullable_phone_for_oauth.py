"""Make phone_number nullable for OAuth-only accounts.

Google OAuth auto-provisioned users no longer get a fabricated placeholder
phone number.  phone_number becomes nullable; uniqueness is preserved via
a partial unique index (WHERE phone_number IS NOT NULL) so multiple NULLs
are allowed while real phone numbers stay unique.

Revision ID: 025_nullable_phone_for_oauth
Revises: 024_add_check_constraints
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "025_nullable_phone_for_oauth"
down_revision = "024_add_check_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(20),
        nullable=True,
    )

    op.drop_index("ix_users_phone_number", table_name="users")

    op.execute(
        "CREATE UNIQUE INDEX ix_users_phone_partial "
        "ON users (phone_number) WHERE phone_number IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_phone_partial")

    op.execute(
        "UPDATE users SET phone_number = '+0000000' || user_id::text "
        "WHERE phone_number IS NULL"
    )

    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)

    op.alter_column(
        "users",
        "phone_number",
        existing_type=sa.String(20),
        nullable=False,
    )
