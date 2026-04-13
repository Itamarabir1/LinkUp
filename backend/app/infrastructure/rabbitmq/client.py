import asyncio
import json
import logging

import aio_pika

from app.core.config import settings
from app.core.exceptions.infrastructure import QueueServiceError

logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self):
        self._connection: aio_pika.abc.AbstractConnection | None = None
        self._channel: aio_pika.abc.AbstractChannel | None = None
        self._exchanges: dict[str, aio_pika.abc.AbstractExchange] = {}
        self._lock = asyncio.Lock()

    async def connect(self):
        """Initial connection — called from application lifespan."""
        async with self._lock:
            if self._connection is None or self._connection.is_closed:
                try:
                    self._connection = await aio_pika.connect_robust(settings.RABBITMQ_URL, timeout=10)
                    self._channel = await self._connection.channel()
                    logger.info("✅ RabbitMQ Client connected")
                except Exception as e:
                    logger.exception("RabbitMQ connect failed: %s", e)
                    raise QueueServiceError() from e

    async def get_channel(self) -> aio_pika.abc.AbstractChannel:
        if not self._channel or self._channel.is_closed:
            await self.connect()
        return self._channel

    async def publish(self, message: dict, routing_key: str, exchange_name: str = ""):
        try:
            channel = await self.get_channel()

            if exchange_name:
                if exchange_name not in self._exchanges:
                    self._exchanges[exchange_name] = await channel.declare_exchange(exchange_name, aio_pika.ExchangeType.TOPIC, durable=True)
                target = self._exchanges[exchange_name]
            else:
                target = channel.default_exchange

            await target.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=routing_key,
            )
        except Exception as e:
            logger.exception(
                "RabbitMQ publish failed routing_key=%s exchange=%s: %s",
                routing_key,
                exchange_name,
                e,
            )
            raise QueueServiceError() from e

    async def close(self):
        async with self._lock:
            if self._connection and not self._connection.is_closed:
                await self._connection.close()
                logger.info("🛑 RabbitMQ Connection closed")

    def is_connected(self) -> bool:
        """For health checks (no await)."""
        if self._connection is None:
            return False
        try:
            return not self._connection.is_closed
        except Exception as e:
            logger.warning("RabbitMQ is_connected check failed: %s", e)
            return False


rabbit_client = RabbitMQClient()
