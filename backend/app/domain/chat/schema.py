"""
Pydantic schemas for 1:1 chat API (request/response).
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConversationCreate(BaseModel):
    """Start or resolve a 1:1 conversation with another user."""

    other_user_id: UUID = Field(..., description="Other participant user id")


_HTML_TAG_RE = re.compile(r"<[^>]+>")


class MessageCreate(BaseModel):
    """Send a message in a conversation."""

    body: str = Field(..., min_length=1, max_length=10_000)

    @field_validator("body")
    @classmethod
    def reject_html(cls, v: str) -> str:
        """Reject messages containing HTML tags — chat is plaintext only."""
        if _HTML_TAG_RE.search(v):
            raise ValueError("הודעות צ'אט לא יכולות להכיל HTML. שלח טקסט בלבד.")
        return v.strip()


# --- Responses ---


class MessageResponse(BaseModel):
    """Single message in API responses."""

    message_id: int
    conversation_id: UUID
    sender_id: UUID
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedMessagesResponse(BaseModel):
    """Cursor-paginated message list."""

    items: list[MessageResponse] = Field(default_factory=list)
    next_cursor: str | None = Field(None, description="Opaque cursor — pass as `after` query param.")
    has_more: bool = False


class MessageGapResponse(BaseModel):
    """Reconnect backfill messages since a known message id."""

    items: list[MessageResponse] = Field(default_factory=list)
    truncated: bool = False
    last_message_id: int | None = None

    @model_validator(mode="after")
    def validate_last_message_id_when_truncated(self) -> "MessageGapResponse":
        if self.truncated and self.last_message_id is None:
            raise ValueError("last_message_id is required when truncated is true")
        return self


class ConversationPartner(BaseModel):
    """Minimal partner profile for conversation lists."""

    user_id: UUID
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(BaseModel):
    """One row in the inbox (partner + optional last message preview)."""

    conversation_id: UUID
    partner: ConversationPartner
    last_message_at: datetime | None = None
    last_message_preview: str | None = None
    has_unread: bool = False

    model_config = ConfigDict(from_attributes=True)


class PaginatedConversationsResponse(BaseModel):
    """Cursor-paginated inbox (conversation list)."""

    items: list[ConversationListItem] = Field(default_factory=list)
    has_more: bool = False
    next_cursor: str | None = Field(None, description="Opaque cursor — pass as `after` query param.")


class ConversationDetail(BaseModel):
    """Full conversation header for open/view (id + partner)."""

    conversation_id: UUID
    partner: ConversationPartner
    created_at: datetime
    booking_id: UUID | None = None  # Set when conversation was opened via a booking
    partner_last_read_at: datetime | None = None
    partner_read_up_to_message_id: int | None = None

    model_config = ConfigDict(from_attributes=True)
