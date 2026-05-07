"""Add missing indexes: bookings.request_id, messages.sender_id.

Revision ID: 012_add_missing_indexes
Revises: 011_chat_read_cursor
Create Date: 2026-04-21
"""

from alembic import op

revision = "012_add_missing_indexes"
down_revision = "011_chat_read_cursor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bookings.request_id -- HIGH risk
    # Used in: determine_passenger_request_status, bulk_cancel_bookings_for_request (e.g. PassengerService.cancel_request)
    op.create_index(
        "idx_bookings_request_id",
        "bookings",
        ["request_id"],
        unique=False,
    )

    # messages.sender_id -- MEDIUM risk
    # Used in: get_unread_conversations_count, mark_conversation_read
    op.create_index(
        "idx_messages_sender_id",
        "messages",
        ["sender_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_messages_sender_id", table_name="messages")
    op.drop_index("idx_bookings_request_id", table_name="bookings")
