import logging
from app.domain.events.schema import Event
from app.domain.events.enum import DispatchTarget
from app.infrastructure.events.publishers.base import EventPublisher

logger = logging.getLogger(__name__)


class RabbitMQPublisher(EventPublisher):
    def __init__(self, rabbit_client):
        self._client = rabbit_client

    async def publish(self, event: Event) -> bool:
        try:
            # שליפה מהמטא-דאטה או שימוש בשם האירוע כברירת מחדל
            routing_key = event.metadata.get("routing_key", event.name) if event.metadata else event.name
            exchange = event.metadata.get("exchange", "system_events") if event.metadata else "system_events"

            await self._client.publish(message=event.payload, routing_key=routing_key, exchange_name=exchange)
            logger.info(
                "[NOTIF] RabbitMQ: published exchange=%s routing_key=%s",
                exchange,
                routing_key,
            )
            return True

        except Exception as e:
            logger.error(f"❌ RabbitMQ publish failed for {event.name}: {e}", exc_info=True)
            raise  # קריטי ל-Rabbit כדי שה-Service ידע שהמשימה לא תוזמנה

    def supports_target(self, target: DispatchTarget) -> bool:
        return target == DispatchTarget.RABBITMQ
