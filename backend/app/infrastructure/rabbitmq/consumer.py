import aio_pika
import json
import logging
from datetime import datetime
from typing import Callable, Awaitable, Dict, Any, Optional, List

logger = logging.getLogger(__name__)

RETRY_DELAYS_SEC = [5, 30, 300]  # 5s, 30s, 5min
MAX_RETRIES = 3
DLQ_EXCHANGE = "dlq_exchange"

# תורים שמקבלים retry + DLQ (לא scheduled)
RETRYABLE_QUEUES = {"notifications_queue", "avatar_upload_queue"}


class RabbitMQConsumer:
    """
    צרכן RabbitMQ. אם מועברת רשימת exchanges – התור נקשרת לכולם (תור אחד לכל המיילים/פוש).
    """

    def __init__(
        self,
        rabbit_client,
        queue_name: str,
        exchange_name: Optional[str] = None,
        exchange_names: Optional[List[str]] = None,
    ):
        self._client = rabbit_client
        self.queue_name = queue_name
        if exchange_names is not None:
            self._exchange_names = exchange_names
        else:
            self._exchange_names = [exchange_name or "system_events"]

    async def _setup(self) -> aio_pika.abc.AbstractQueue:
        """מכריז על תור וקושר אותו לכל ה-exchanges (תור אחד מקבל הודעות מכל הדומיינים)."""
        channel = await self._client.get_channel()
        self._channel = channel
        await channel.set_qos(prefetch_count=10)

        if self.queue_name in RETRYABLE_QUEUES:
            dlq_exchange = await channel.declare_exchange(
                DLQ_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            dlq_queue = await channel.declare_queue(
                f"{self.queue_name}.dlq",
                durable=True,
            )
            await dlq_queue.bind(dlq_exchange, routing_key=f"{self.queue_name}.dlq")

            await channel.declare_queue(
                f"{self.queue_name}.retry",
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": self.queue_name,
                },
            )

            queue = await channel.declare_queue(
                self.queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": DLQ_EXCHANGE,
                    "x-dead-letter-routing-key": f"{self.queue_name}.dlq",
                },
            )
        else:
            queue = await channel.declare_queue(self.queue_name, durable=True)

        for ex_name in self._exchange_names:
            exchange = await channel.declare_exchange(ex_name, aio_pika.ExchangeType.TOPIC, durable=True)
            await queue.bind(exchange, routing_key="#")
            logger.debug("Queue %s bound to exchange %s", self.queue_name, ex_name)
        return queue

    async def consume(self, callback: Callable[[Dict[str, Any], str], Awaitable[None]]):
        """אחראי רק על לופ ההאזנה והעברת הודעות ל-Callback"""
        self._callback = callback
        queue = await self._setup()
        logger.info(f"✅ Consumer ready on '{self.queue_name}'")

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                await self._process_message(message)

    async def _handle_with_retry(
        self,
        message: aio_pika.IncomingMessage,
        callback: Callable,
        queue_name: str,
    ) -> None:
        retry_count = int(message.headers.get("x-retry-count", 0))

        try:
            payload = json.loads(message.body)
        except Exception as e:
            logger.error("Failed to parse message body: %s", e)
            await message.nack(requeue=False)
            return

        try:
            logger.info(
                "[NOTIF] RabbitMQ: received routing_key=%s payload_keys=%s",
                message.routing_key,
                list(payload.keys()) if isinstance(payload, dict) else "?",
            )
            await callback(payload, message.routing_key)
            await message.ack()
        except Exception as e:
            if retry_count < MAX_RETRIES:
                delay = RETRY_DELAYS_SEC[retry_count]
                logger.warning(
                    "Message failed (attempt %s/%s), retrying in %ss. Queue: %s. Error: %s",
                    retry_count + 1,
                    MAX_RETRIES,
                    delay,
                    queue_name,
                    e,
                )
                await self._channel.default_exchange.publish(
                    aio_pika.Message(
                        body=message.body,
                        headers={
                            **dict(message.headers or {}),
                            "x-retry-count": retry_count + 1,
                            "x-original-queue": queue_name,
                        },
                        expiration=str(delay * 1000),
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=f"{queue_name}.retry",
                )
                await message.ack()
            else:
                body_preview = message.body[:500].decode(errors="replace")
                logger.error(
                    "DEAD_LETTER",
                    extra={
                        "queue": queue_name,
                        "retry_count": retry_count,
                        "error": str(e),
                        "message_body": body_preview,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                await message.nack(requeue=False)

    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        """ניהול לוגיקת העיבוד של הודעה בודדת. תורים ב-RETRYABLE_QUEUES מקבלים retry + DLQ."""
        if self.queue_name in RETRYABLE_QUEUES:
            await self._handle_with_retry(message, self._callback, self.queue_name)
        else:
            async with message.process():
                try:
                    payload = json.loads(message.body)
                    await self._callback(payload, message.routing_key)
                except Exception as e:
                    logger.error("Task failed: %s", e, exc_info=True)
