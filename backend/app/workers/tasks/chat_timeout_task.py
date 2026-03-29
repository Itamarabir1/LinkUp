"""
Scheduled task לבדיקת שיחות עם timeout 24 שעות ללא הודעות חדשות.
"""

import logging

from app.db.session import SessionLocal
from app.domain.chat import crud as chat_crud
from app.domain.chat.completion.service import handle_conversation_completion

logger = logging.getLogger(__name__)


async def execute_chat_timeout_job():
    """
    בודק שיחות שלא נשלח להן סיכום ושההודעה האחרונה בהן היא לפני 24 שעות.
    מטפל בכל שיחה: ניתוח AI + שליחת event.
    """
    async with SessionLocal() as db:
        try:
            # שליפת שיחות עם timeout
            conversations = await chat_crud.get_conversations_with_timeout(db, timeout_hours=24)

            if not conversations:
                logger.info("No conversations with timeout found")
                return

            logger.info(f"Found {len(conversations)} conversations with timeout, processing...")

            # טיפול בכל שיחה
            for conv in conversations:
                try:
                    # ניסיון לטפל בסיום השיחה (ניתוח AI + event)
                    # נשתמש ב-user_id_1 כ-current_user_id (רק לבדיקת הרשאות)
                    success = await handle_conversation_completion(
                        db=db,
                        conversation_id=conv.conversation_id,
                        current_user_id=conv.user_id_1,
                    )
                    if success:
                        logger.info(f"Successfully processed timeout for conversation {conv.conversation_id}")
                    else:
                        logger.warning(f"Failed to process timeout for conversation {conv.conversation_id}")
                except Exception as e:
                    logger.error(
                        f"Error processing conversation {conv.conversation_id}: {e}",
                        exc_info=True,
                    )
                    # ממשיכים לשיחה הבאה גם אם יש שגיאה
                    continue

            logger.info(f"Completed processing {len(conversations)} conversations with timeout")

        except Exception as e:
            logger.error(f"Error in chat timeout job: {e}", exc_info=True)
            raise
