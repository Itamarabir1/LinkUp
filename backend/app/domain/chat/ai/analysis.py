"""
ניתוח AI של שיחות צ'אט - שירותים לניתוח ושימוש בתוצאות.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat import crud as chat_crud

logger = logging.getLogger(__name__)


async def get_conversation_text_for_analysis(
    db: AsyncSession,
    conversation_id: UUID,
    current_user_id: UUID,
    limit: int = 50,
) -> str | None:
    """
    אוסף את טקסט השיחה לניתוח AI.
    מחזיר None אם המשתמש לא participant או השיחה לא קיימת.

    Returns:
        מחרוזת טקסט בפורמט: "User_{sender_id}: {body}\nUser_{sender_id}: {body}..."
    """
    # Ensure user is a participant
    conv = await chat_crud.get_conversation_by_id(db, conversation_id, current_user_id)
    if not conv:
        return None

    # Load messages (internal — no pagination)
    messages = await chat_crud.get_all_messages_for_conversation(
        db,
        conversation_id=conversation_id,
        limit=limit,
    )

    if not messages:
        return None

    # Build conversation text
    conversation_lines = []
    for msg in messages:
        conversation_lines.append(f"User_{msg.sender_id}: {msg.body}")

    return "\n".join(conversation_lines)
