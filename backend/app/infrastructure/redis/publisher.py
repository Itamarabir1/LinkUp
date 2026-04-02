"""
publisher.py — נקודת הכניסה היחידה לשידור אירועים דרך Redis Pub/Sub.
ניטרלי לדומיין. כל שידור עובר דרך כאן בלבד.
"""
import json
import logging
from uuid import UUID
from app.infrastructure.redis.broadcast import broadcast
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
    payload = {"event": event, "user_id": str(user_id), **(extra or {})}
    try:
        await broadcast.publish(get_user_channel(user_id), json.dumps(payload))
    except Exception as e:
        logger.warning("publish_user_event failed [%s] user=%s: %s", event, user_id, e)
