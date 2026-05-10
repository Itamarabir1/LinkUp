import json
import logging

from app.domain.events.enum import DispatchTarget
from app.domain.events.schema import Event
from app.infrastructure.events.publishers.base import EventPublisher
from app.infrastructure.redis.chat_pubsub import RedisChatPubSub

logger = logging.getLogger(__name__)


class RedisChatPublisher(EventPublisher):
    """Publishes chat.message_sent events to Redis chat:conversation:* channels."""

    def __init__(self, pubsub: RedisChatPubSub) -> None:
        self._pubsub = pubsub

    def supports_target(self, target: DispatchTarget) -> bool:
        return target == DispatchTarget.REDIS

    async def publish(self, event: Event) -> bool:
        try:
            if event.name == "chat.message_sent":
                conversation_id = event.payload.get("conversation_id")
                if not conversation_id:
                    logger.error("RedisChatPublisher: chat.message_sent missing conversation_id")
                    return False
                channel = f"chat:conversation:{conversation_id}"
                message = json.dumps(event.payload)
                count = await self._pubsub.publish(channel, message)
                if count == 0:
                    logger.warning("RedisChatPublisher: 0 subscribers on channel=%s", channel)
                return True
            logger.warning("RedisChatPublisher: unhandled event name=%s", event.name)
            return False
        except Exception as e:
            logger.error("RedisChatPublisher.publish failed event=%s: %s", event.name, e)
            raise
