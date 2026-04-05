"""
טיפול באירועי סיום שיחה מ-Redis DB=1: ניתוח AI ושמירה.
מאזין לערוץ chat:completion:* ומפעיל את handle_conversation_completion (domain/chat/ai).
"""

import asyncio
import json
import logging
from uuid import UUID

import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions.infrastructure import WorkerTaskFailed
from app.db.session import SessionLocal
from app.domain.chat.completion.service import handle_conversation_completion

logger = logging.getLogger(__name__)

CHAT_COMPLETION_PATTERN = "chat:completion:*"


async def _process_completion_message(payload_str: str) -> None:
    """מפרסר את ה-payload ומפעיל ניתוח AI + שמירה."""
    try:
        data = json.loads(payload_str)
        conversation_id = data.get("conversation_id")
        trigger_user_id = data.get("trigger_user_id")
        if conversation_id is None or trigger_user_id is None:
            logger.error(
                "chat completion event missing conversation_id or trigger_user_id: %s",
                data,
            )
            raise WorkerTaskFailed(message="אירוע סיום צ'אט חסר conversation_id או trigger_user_id")
        cid = UUID(str(conversation_id))
        uid = UUID(str(trigger_user_id))
        async with SessionLocal() as db:
            try:
                await handle_conversation_completion(db, cid, uid)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.exception(
                    "chat completion DB handler failed conversation_id=%s: %s",
                    cid,
                    e,
                )
                raise WorkerTaskFailed() from e
    except WorkerTaskFailed:
        raise
    except Exception as e:
        logger.error("Error processing chat completion event: %s", e, exc_info=True)
        raise WorkerTaskFailed() from e


async def run_chat_completion_redis_listener(stop_event: asyncio.Event) -> None:
    """
    מאזין ל-Redis DB=1 (REDIS_CHAT_URL) לערוצים chat:completion:*.
    כשמגיע אירוע — מפעיל handle_conversation_completion (ניתוח AI + שמירה + outbox).
    """
    client = None
    try:
        client = redis.from_url(settings.REDIS_CHAT_URL, decode_responses=True)
        pubsub = client.pubsub()
        await pubsub.psubscribe(CHAT_COMPLETION_PATTERN)
        logger.info(
            "Chat completion listener subscribed to %s (Redis DB=1)",
            CHAT_COMPLETION_PATTERN,
        )

        while not stop_event.is_set():
            try:
                message = await asyncio.wait_for(pubsub.get_message(timeout=1.0), timeout=2.0)
            except TimeoutError:
                continue
            if message is None:
                continue
            if message["type"] != "pmessage":
                continue
            try:
                payload = message.get("data")
                if isinstance(payload, str):
                    await _process_completion_message(payload)
            except Exception as e:
                logger.error("Chat completion listener message error: %s", e, exc_info=True)
    except asyncio.CancelledError:
        logger.info("Chat completion listener cancelled.")
    except Exception as e:
        logger.error("Chat completion listener error: %s", e, exc_info=True)
    finally:
        if client:
            await client.close()
        logger.info("Chat completion listener stopped.")
