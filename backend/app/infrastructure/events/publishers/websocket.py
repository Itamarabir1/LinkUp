import json
import logging

from backend.app.infrastructure.events.publishers.base import EventPublisher
from backend.app.infrastructure.outbox.model import DispatchTarget, Event

logger = logging.getLogger(__name__)


class WebSocketPublisher(EventPublisher):
    def __init__(self, redis_broadcast):
        self._broadcast = redis_broadcast

    async def publish(self, event: Event) -> bool:
        try:
            channels = event.metadata.get("channels", []) if event.metadata else []
            if not channels:
                logger.warning(f"⚠️ No channels specified for WebSocket event {event.name}")
                return False

            ws_message = json.dumps(
                {
                    "type": event.name,
                    "data": event.payload,
                    "timestamp": event.payload.get("timestamp"),
                },
            )

            for channel in channels:
                await self._broadcast.publish(channel=channel, message=ws_message)

            logger.debug(f"✅ WebSocket: Published {event.name} → {channels}")
            return True

        except Exception as e:
            logger.error(f"❌ WebSocket publish failed for {event.name}: {e}", exc_info=True)
            raise

    def supports_target(self, target: DispatchTarget) -> bool:
        return target == DispatchTarget.WEBSOCKET
