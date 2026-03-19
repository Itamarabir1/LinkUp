import json
import logging
from typing import Any, Dict, Union
from app.domain.notifications.providers.base import BaseNotificationProvider
from app.infrastructure.redis.broadcast import broadcast

logger = logging.getLogger(__name__)


class WebSocketProvider(BaseNotificationProvider):
    """
    WebSocket Provider (Real-time UI Updates).
    פרסום לערוץ Redis user_{id} — ה-API מזרים ל-WebSocket של המשתמש.
    """

    def can_send(self, user: Any) -> bool:
        uid = getattr(user, "user_id", None) or getattr(user, "id", None)
        return bool(user and uid)

    async def send(
        self,
        user: Any,
        template: Union[str, Dict[str, Any]],
        context: Dict[str, Any],
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
            payload = {"type": "notifications_refresh", "event": event_key}
        else:
            payload = {"type": "UI_UPDATE", "event": event_key}

        channel = f"user_{user_id}"

        try:
            # 2. שליחה ל-Redis
            # סניור משתמש ב-default=str כדי שכל אובייקט (כמו UUID) יומר למחרוזת בבטחה
            message_json = json.dumps(payload, ensure_ascii=False, default=str)

            await broadcast.publish(channel=channel, message=message_json)
            logger.debug(f"📡 [WS Provider] Published to {channel}")

        except Exception as e:
            logger.error(f"❌ [WS Provider] Redis Publish Failed: {str(e)}")
            # לא זורקים שגיאה כדי שכישלון ב-WS לא יפיל שליחת מייל או פוש
