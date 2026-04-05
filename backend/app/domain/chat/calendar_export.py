"""
ייצוא שיחות צ'אט ללוח שנה (iCal).
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat import crud as chat_crud

logger = logging.getLogger(__name__)


async def get_conversation_for_calendar_export(
    db: AsyncSession,
    conversation_id: int,
    current_user_id: int,
) -> dict | None:
    """
    אוסף נתוני שיחה לייצוא ללוח שנה.
    מחזיר None אם המשתמש לא participant או השיחה לא קיימת.

    Returns:
        dict עם:
        - conversation_id
        - messages (רשימת הודעות)
        - partner (הצד השני)
    """
    # וידוא שהמשתמש participant
    conv = await chat_crud.get_conversation_by_id(db, conversation_id, current_user_id)
    if not conv:
        return None

    # איסוף הודעות (פנימי – לא pagination)
    messages = await chat_crud.get_all_messages_for_conversation(
        db,
        conversation_id=conversation_id,
        limit=100,
    )

    # זיהוי הצד השני
    partner_user = conv.user_2 if conv.user_id_1 == current_user_id else conv.user_1

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "partner": {
            "user_id": partner_user.user_id,
            "full_name": partner_user.full_name,
        },
        "current_user_id": current_user_id,
    }
