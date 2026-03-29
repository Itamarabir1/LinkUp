"""
Publish chat completion events to Redis DB=1 (REDIS_CHAT_URL).
Used to trigger async AI summary via worker listener; does not run AI in request path.
"""

import json
import logging
import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions.infrastructure import RedisUnavailable

logger = logging.getLogger(__name__)


async def publish_chat_completion_event(conversation_id: int, trigger_user_id: int) -> int:
    """
    מפרסם אירוע סיום שיחה ל-Redis DB=1 לערוץ chat:completion:{conversation_id}.
    ה-worker מאזין ומפעיל ניתוח AI (Celery/async).
    """
    payload = {"conversation_id": conversation_id, "trigger_user_id": trigger_user_id}
    channel = f"chat:completion:{conversation_id}"
    client = None
    try:
        client = await redis.from_url(
            settings.REDIS_CHAT_URL,
            decode_responses=True,
        )
        n = await client.publish(channel, json.dumps(payload))
        logger.debug("Published chat completion event to %s (%d subscriber(s))", channel, n)
        return n
    except Exception as e:
        logger.error(
            "Failed to publish chat completion event to %s: %s",
            channel,
            e,
            exc_info=True,
        )
        raise RedisUnavailable() from e
    finally:
        if client:
            await client.close()
