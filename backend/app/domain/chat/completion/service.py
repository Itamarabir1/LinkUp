"""
Service לזיהוי סיום שיחה, ניתוח AI, ושמירת תוצאות.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BATCH_SIZE_DEFAULT
from app.domain.chat import crud as chat_crud
from app.domain.chat.ai.analysis import get_conversation_text_for_analysis
from app.domain.chat.ai.analyzer import analyze_conversation
from app.domain.chat.ai.crud import analysis_exists, create_analysis
from app.domain.events.outbox import publish_to_outbox

logger = logging.getLogger(__name__)


async def handle_conversation_completion(
    db: AsyncSession,
    conversation_id: UUID,
    current_user_id: UUID,
) -> bool:
    """
    מטפל בסיום שיחה: בודק אם כבר נותח, מנתח, שומר, ושולח event.

    Args:
        db: AsyncSession
        conversation_id: מזהה השיחה
        current_user_id: מזהה המשתמש הנוכחי (לבדיקת הרשאות)

    Returns:
        True אם הצליח, False אחרת
    """
    try:
        # בדיקה שהשיחה קיימת והמשתמש participant
        conv = await chat_crud.get_conversation_by_id(db, conversation_id, current_user_id)
        if not conv:
            logger.warning(f"Conversation {conversation_id} not found or user {current_user_id} not participant")
            return False

        # בדיקה אם כבר נותח (idempotency)
        if await analysis_exists(db, conversation_id):
            logger.info(f"Conversation {conversation_id} already analyzed, skipping")
            return False

        # איסוף טקסט השיחה
        chat_text = await get_conversation_text_for_analysis(db, conversation_id, current_user_id, limit=BATCH_SIZE_DEFAULT)
        if not chat_text:
            logger.warning(f"No messages found for conversation {conversation_id}")
            return False

        # ניתוח AI
        ride_summary = analyze_conversation(chat_text)
        if not ride_summary:
            logger.error(f"AI analysis failed for conversation {conversation_id}")
            return False

        # שמירה ב-DB
        await create_analysis(
            db=db,
            conversation_id=conversation_id,
            driver_name=ride_summary.driver_name,
            passenger_name=ride_summary.passenger_name,
            pickup_location=ride_summary.pickup_location,
            meeting_time=ride_summary.meeting_time,
            summary_hebrew=ride_summary.summary_hebrew,
            analysis_json=ride_summary.model_dump(),
        )

        # שליחת event ל-RabbitMQ (דרך Outbox)
        await publish_to_outbox(
            db=db,
            event_name="chat.conversation.completed",
            payload={
                "conversation_id": str(conversation_id),
                "user_id_1": str(conv.user_id_1),
                "user_id_2": str(conv.user_id_2),
                "driver_name": ride_summary.driver_name,
                "passenger_name": ride_summary.passenger_name,
                "pickup_location": ride_summary.pickup_location,
                "meeting_time": ride_summary.meeting_time,
                "summary_hebrew": ride_summary.summary_hebrew,
            },
        )

        logger.info(f"Conversation {conversation_id} completed and analyzed successfully")
        return True

    except Exception as e:
        logger.error(f"Error handling conversation completion: {e}", exc_info=True)
        return False
