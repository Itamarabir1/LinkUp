"""
סכמות צ'אט 1:1 – קלט/פלט ל־API.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """פתיחת שיחה עם משתמש – מזהה או יוצר שיחה 1:1."""

    other_user_id: UUID = Field(..., description="מזהה המשתמש השני")


class MessageCreate(BaseModel):
    """שליחת הודעה בשיחה."""

    body: str = Field(..., min_length=1, max_length=10_000)


# --- Responses ---


class MessageResponse(BaseModel):
    """הודעה אחת בתשובה."""

    message_id: int
    conversation_id: UUID
    sender_id: UUID
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedMessagesResponse(BaseModel):
    """הודעות בשיחה עם pagination (cursor-based)."""

    items: list[MessageResponse] = Field(default_factory=list)
    next_cursor: str | None = Field(None, description="message_id של הישן ביותר להבא (before=)")
    has_more: bool = False


class ConversationPartner(BaseModel):
    """מידע מינימלי על הצד השני בשיחה (להרשימה)."""

    user_id: UUID
    full_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConversationListItem(BaseModel):
    """שיחה אחת ברשימת השיחות שלי (עם פרטי הצד השני והודעה אחרונה אופציונלית)."""

    conversation_id: UUID
    partner: ConversationPartner
    last_message_at: datetime | None = None
    last_message_preview: str | None = None
    has_unread: bool = False

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(BaseModel):
    """שיחה מלאה – לפתיחה/צפייה (מזהה + פרטי הצד השני)."""

    conversation_id: UUID
    partner: ConversationPartner
    created_at: datetime
    booking_id: UUID | None = None  # קישור ל-booking אם השיחה נוצרה דרך booking

    model_config = ConfigDict(from_attributes=True)
