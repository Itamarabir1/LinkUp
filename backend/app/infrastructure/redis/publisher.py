"""
publisher.py — entry point for publishing domain events over Redis Pub/Sub.
- ride: broadcast (REDIS_URL / DB0) — aligns with FastAPI WS on ride_*.
- user (chat-ws): redis_chat_pubsub (REDIS_CHAT_URL) — same DB as chat-ws.
"""

import json
import logging
from uuid import UUID

from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.infrastructure.redis.keys import get_ride_channel, get_user_channel

logger = logging.getLogger(__name__)


async def publish_ride_event(
    ride_id: UUID,
    event: str,
    extra: dict | None = None,
) -> None:
    payload = {"event": event, "ride_id": str(ride_id), **(extra or {})}
    try:
        await broadcast.publish(get_ride_channel(ride_id), json.dumps(payload))
    except Exception as e:
        logger.warning("publish_ride_event failed [%s]: %s", event, e)


async def publish_user_event(
    user_id: UUID,
    event: str,
    extra: dict | None = None,
) -> None:
    """Pub/Sub on REDIS_CHAT_URL (same DB as chat-ws) — not broadcast/DB 0."""
    payload = {"event": event, "user_id": str(user_id), **(extra or {})}
    try:
        n = await redis_chat_pubsub.publish(get_user_channel(user_id), json.dumps(payload))
        if n == 0 and redis_chat_pubsub.client is None:
            logger.warning(
                "publish_user_event skipped (chat redis not connected) [%s] user=%s",
                event,
                user_id,
            )
    except Exception as e:
        logger.warning("publish_user_event failed [%s] user=%s: %s", event, user_id, e)
