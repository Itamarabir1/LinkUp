import json
import logging
from typing import Any

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
    ) -> None:
        user_id = getattr(user, "user_id", None) or getattr(user, "id", None)
        if not user_id:
            logger.error("❌ [WS Provider] User object has no ID")
            return

        event_key = context.get("event_key") or ""

        REFRESH_EVENTS = {
            "booking.passenger_join_request",
            "booking.approved_by_driver",
            "booking.rejected_by_driver",
            "ride.cancelled_by_driver",
        }

        if event_key in REFRESH_EVENTS:
            payload = {
                "type": "notifications_refresh",
                "event": event_key,
                "user_id": str(user_id),
            }
        else:
            payload = {
                "type": "UI_UPDATE",
                "event": event_key,
                "user_id": str(user_id),
            }

        channel = f"user:{user_id}:events"

        try:
            message_json = json.dumps(payload, ensure_ascii=False, default=str)
            await redis_chat_pubsub.publish(channel, message_json)
            logger.debug(f"📡 [WS Provider] Published to {channel}")

        except Exception as e:
            logger.error(f"❌ [WS Provider] Redis Publish Failed: {e!s}")
            # Swallow errors so WS failure does not break email or push
