"""
פרסום אירועי צ'אט ל-Redis Pub/Sub – שרת ה-WS (Go) מאזין לערוצים ומוסר ל-WebSocket.
אין הגדרה מיוחדת ב-Redis – Pub/Sub מובנה בכל Redis.
"""

import json
import logging
from typing import Any
from uuid import UUID

from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub

logger = logging.getLogger(__name__)

CHAT_CHANNEL_PREFIX = "chat:conversation:"


def _channel(conversation_id: UUID) -> str:
    return f"{CHAT_CHANNEL_PREFIX}{conversation_id}"


async def publish_chat_message(conversation_id: UUID, payload: dict[str, Any]) -> int:
    """
    מפרסם הודעת צ'אט לערוץ Redis. שרת ה-WS (Go) מאזין ל־chat:conversation:* ומעביר ל-WebSocket.
    payload: למשל { "message_id", "conversation_id", "sender_id", "body", "created_at" } (כ־ISO string).
    """
    channel = _channel(conversation_id)
    message = json.dumps(payload, default=str)
    count = await redis_chat_pubsub.publish(channel, message)
    if count > 0:
        logger.debug("Published chat message to %s (%d subscriber(s))", channel, count)
    return count
