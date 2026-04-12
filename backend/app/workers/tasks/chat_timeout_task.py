"""
Scheduled job: conversations idle 24h without new messages → completion flow.
"""

import logging

from app.db.session import SessionLocal
from app.domain.chat import crud as chat_crud
from app.domain.chat.completion.service import handle_conversation_completion

logger = logging.getLogger(__name__)


async def execute_chat_timeout_job():
    """
    Find timed-out conversations and run AI completion + outbox for each.
    """
    async with SessionLocal() as db:
        try:
            # Conversations past idle timeout
            conversations = await chat_crud.get_conversations_with_timeout(db, timeout_hours=24)

            if not conversations:
                logger.info("No conversations with timeout found")
                return

            logger.info(f"Found {len(conversations)} conversations with timeout, processing...")

            # Iterate conversations
            for conv in conversations:
                try:
                    # Run completion flow (AI + outbox event)
                    # Use user_id_1 only for auth guard inside service
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
                    # Continue batch on single-conversation errors
                    continue

            logger.info(f"Completed processing {len(conversations)} conversations with timeout")

        except Exception as e:
            logger.error(f"Error in chat timeout job: {e}", exc_info=True)
            raise
