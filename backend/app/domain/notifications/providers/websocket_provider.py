import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.notifications.providers.base import BaseNotificationProvider
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub

logger = logging.getLogger(__name__)


class WebSocketProvider(BaseNotificationProvider):
    """
    WebSocket Provider (Real-time UI Updates).
    Publishes user-specific events to Redis chat pub/sub (DB1) channel user:{id}:events.
    """

    def can_send(self, user: Any) -> bool:
        uid = getattr(user, "user_id", None) or getattr(user, "id", None)
        return bool(user and uid)

    async def send(
        self,
        user: Any,
        template: str | dict[str, Any],
        context: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> None:
        user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
        if not user_id:
            logger.error("[WS Provider] User object has no ID")
            return

        event_key = context.get("event_key") or ""

        payload = {
            "type": "invalidate",
            "resource": "notifications",
            "event": event_key,
            "user_id": str(user_id),
        }

        channel = f"user:{user_id}:events"

        try:
            await redis_chat_pubsub.publish(channel, json.dumps(payload, ensure_ascii=False, default=str))
            logger.debug("[WS Provider] Published to %s", channel)
        except Exception as e:
            logger.error("[WS Provider] Redis Publish Failed: %s", e, exc_info=False)
