import json
import logging
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import aio_pika
from app.infrastructure.metrics import (
    rabbitmq_consumer_iterator_restarts_total,
    rabbitmq_messages_consumed_total,
    rabbitmq_messages_failed_total,
    rabbitmq_messages_retried_total,
)
from app.infrastructure.rabbitmq.topology import get_queue_spec

logger = logging.getLogger(__name__)

# Dedicated exchanges used by broker-native retry and DLQ routing.
DLQ_EXCHANGE = "dlq_exchange"
RETRY_EXCHANGE = "retry_exchange"


class ConsumerState(str, Enum):
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"


class ConsumerSupervisor:
    """
    Tracks message tasks and drains in-flight work on shutdown.
    """

    def __init__(self, consumer_name: str, drain_timeout_seconds: int = 30):
        self.consumer_name = consumer_name
        self.drain_timeout_seconds = drain_timeout_seconds
        self.state = ConsumerState.RUNNING
        self.accepting_deliveries = True
        self._inflight_tasks: set[asyncio.Task[Any]] = set()

    def track_task(self, task: asyncio.Task[Any]) -> None:
        self._inflight_tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        self._inflight_tasks.discard(task)
        try:
            task.result()
        except Exception as e:
            logger.error("Consumer task failed consumer=%s: %s", self.consumer_name, e, exc_info=True)

    def start_draining(self) -> None:
        if self.state != ConsumerState.RUNNING:
            return
        self.state = ConsumerState.DRAINING
        self.accepting_deliveries = False
        logger.info("Consumer entering DRAINING state consumer=%s inflight=%s", self.consumer_name, len(self._inflight_tasks))

    async def drain(self) -> bool:
        if not self._inflight_tasks:
            self.state = ConsumerState.STOPPED
            return True

        done, pending = await asyncio.wait(self._inflight_tasks, timeout=self.drain_timeout_seconds)
        if pending:
            logger.warning(
                "Consumer drain timeout consumer=%s done=%s pending=%s timeout=%ss",
                self.consumer_name,
                len(done),
                len(pending),
                self.drain_timeout_seconds,
            )
            for task in pending:
                task.cancel()
            await asyncio.wait(pending, timeout=5)
            self.state = ConsumerState.STOPPED
            return False

        self.state = ConsumerState.STOPPED
        logger.info("Consumer drained cleanly consumer=%s", self.consumer_name)
        return True


def get_retry_count_from_xdeath(headers: dict[str, Any] | None, queue_name: str) -> int:
    """
    Queue-scoped x-death parser.
    x-death is a list of dictionaries; only entries for the current queue count.
    """
    if not headers:
        return 0
    x_death = headers.get("x-death", [])
    if not isinstance(x_death, list):
        return 0
    total = 0
    for entry in x_death:
        if not isinstance(entry, dict):
            continue
        if entry.get("queue") != queue_name:
            continue
        count = entry.get("count", 0)
        try:
            total += int(count)
        except (TypeError, ValueError):
            continue
    return total


class RabbitMQConsumer:
    """
    RabbitMQ consumer. If a list of exchanges is passed, the queue is bound to all of them
    (one queue for all notification mail/push traffic).
    """

    def __init__(
        self,
        rabbit_client,
        queue_name: str,
        exchange_name: str | None = None,
        exchange_names: list[str] | None = None,
    ):
        self._client = rabbit_client
        self.queue_name = queue_name
        self._exchange_names_override = exchange_names if exchange_names is not None else None
        self._exchange_name_fallback = exchange_name

    async def _setup(self) -> aio_pika.abc.AbstractQueue:
        """Declares the queue and binds it to every exchange (one queue receives messages from all domains)."""
        spec = get_queue_spec(self.queue_name, exchange_names_override=self._exchange_names_override)
        exchange_names = list(spec.exchange_names) or [self._exchange_name_fallback or "system_events"]

        channel = await self._client.get_consumer_channel(self.queue_name)
        self._channel = channel
        await channel.set_qos(prefetch_count=spec.prefetch_count)

        if spec.retry_enabled:
            self._dlq_exchange = await channel.declare_exchange(
                DLQ_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            retry_exchange = await channel.declare_exchange(
                RETRY_EXCHANGE,
                aio_pika.ExchangeType.DIRECT,
                durable=True,
            )
            dlq_queue = await channel.declare_queue(
                f"{self.queue_name}.dlq",
                durable=True,
            )
            await dlq_queue.bind(self._dlq_exchange, routing_key=f"{self.queue_name}.dlq")

            retry_queue = await channel.declare_queue(
                f"{self.queue_name}.retry",
                durable=True,
                arguments={
                    "x-message-ttl": spec.retry_delay_ms,
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": self.queue_name,
                },
            )
            await retry_queue.bind(retry_exchange, routing_key=f"{self.queue_name}.retry")

            queue = await channel.declare_queue(
                self.queue_name,
                durable=spec.durable,
                arguments={
                    "x-dead-letter-exchange": RETRY_EXCHANGE,
                    "x-dead-letter-routing-key": f"{self.queue_name}.retry",
                },
            )
        else:
            queue = await channel.declare_queue(self.queue_name, durable=spec.durable)

        for ex_name in exchange_names:
            exchange = await channel.declare_exchange(ex_name, aio_pika.ExchangeType.TOPIC, durable=True)
            await queue.bind(exchange, routing_key="#")
            logger.debug("Queue %s bound to exchange %s", self.queue_name, ex_name)
        return queue

    async def consume(
        self,
        callback: Callable[[dict[str, Any], str], Awaitable[None]],
        stop_event: asyncio.Event | None = None,
    ):
        """
        Self-healing consume loop. Owns iterator recreation on channel/iterator close
        and bounded backoff on _setup() failures. Returns to supervisor only when
        stop_event is set or an unrecoverable programming error occurs.
        """
        self._callback = callback
        backoff_seconds = 1.0
        MAX_BACKOFF_SECONDS = 30.0

        while not (stop_event and stop_event.is_set()):
            supervisor = ConsumerSupervisor(consumer_name=self.queue_name)
            try:
                queue = await self._setup()
                backoff_seconds = 1.0
                logger.info("✅ Consumer ready on '%s'", self.queue_name)

                async with queue.iterator() as queue_iter:
                    while not (stop_event and stop_event.is_set()):
                        try:
                            message = await asyncio.wait_for(queue_iter.__anext__(), timeout=1)
                        except asyncio.TimeoutError:
                            continue
                        except StopAsyncIteration:
                            rabbitmq_consumer_iterator_restarts_total.labels(queue=self.queue_name).inc()
                            logger.warning("Iterator closed for '%s', will recreate", self.queue_name)
                            break

                        if not supervisor.accepting_deliveries:
                            await message.nack(requeue=False)
                            continue
                        task = asyncio.create_task(self._process_message(message))
                        supervisor.track_task(task)

                supervisor.start_draining()
                await supervisor.drain()

            except asyncio.CancelledError:
                supervisor.start_draining()
                await supervisor.drain()
                raise
            except Exception as e:
                logger.error("Consumer recoverable error on '%s': %s", self.queue_name, e, exc_info=True)
                supervisor.start_draining()
                await supervisor.drain()

                if stop_event and stop_event.is_set():
                    return
                await self._sleep_or_stop(backoff_seconds, stop_event)
                backoff_seconds = min(MAX_BACKOFF_SECONDS, backoff_seconds * 2)

    async def _sleep_or_stop(self, seconds: float, stop_event: asyncio.Event | None) -> None:
        """Sleep, but wake up immediately if stop_event fires."""
        if stop_event is None:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return

    async def _handle_with_retry(
        self,
        message: aio_pika.IncomingMessage,
        callback: Callable,
        queue_name: str,
    ) -> None:
        spec = get_queue_spec(self.queue_name, exchange_names_override=self._exchange_names_override)
        headers = dict(message.headers or {})
        xdeath_retry_count = get_retry_count_from_xdeath(headers, queue_name)

        try:
            payload = json.loads(message.body)
        except Exception as e:
            logger.error("Failed to parse message body: %s", e)
            await message.nack(requeue=False)
            return

        try:
            logger.info(
                "[NOTIF] RabbitMQ: routing_key=%s payload_keys=%s xdeath_queue_count=%s max_retries=%s",
                message.routing_key,
                list(payload.keys()) if isinstance(payload, dict) else "?",
                xdeath_retry_count,
                spec.max_retries,
            )
            await callback(payload, message.routing_key)
            await message.ack()
            rabbitmq_messages_consumed_total.labels(queue=queue_name).inc()
        except Exception as e:
            if xdeath_retry_count < spec.max_retries:
                logger.warning(
                    "Message failed (attempt %s/%s), nacking to broker retry queue. queue=%s error=%s",
                    xdeath_retry_count + 1,
                    spec.max_retries,
                    queue_name,
                    e,
                )
                await message.nack(requeue=False)
                rabbitmq_messages_retried_total.labels(queue=queue_name).inc()
                return

            body_preview = message.body[:500].decode(errors="replace")
            logger.error(
                "DEAD_LETTER",
                extra={
                    "queue": queue_name,
                    "retry_count": xdeath_retry_count,
                    "error": str(e),
                    "message_body": body_preview,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
            )
            await self._dlq_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers=dict(message.headers or {}),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=f"{queue_name}.dlq",
            )
            await message.ack()
            rabbitmq_messages_failed_total.labels(queue=queue_name).inc()

    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Handles processing logic for a single message. Queues in RETRYABLE_QUEUES get retry + DLQ."""
        spec = get_queue_spec(self.queue_name, exchange_names_override=self._exchange_names_override)
        if spec.retry_enabled:
            await self._handle_with_retry(message, self._callback, self.queue_name)
        else:
            try:
                payload = json.loads(message.body)
                await self._callback(payload, message.routing_key)
                await message.ack()
                rabbitmq_messages_consumed_total.labels(queue=self.queue_name).inc()
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON, discarding queue=%s: %s", self.queue_name, e)
                await message.nack(requeue=False)
                rabbitmq_messages_failed_total.labels(queue=self.queue_name).inc()
            except Exception as e:
                logger.error("Task failed, discarding queue=%s: %s", self.queue_name, e, exc_info=True)
                await message.nack(requeue=False)
                rabbitmq_messages_failed_total.labels(queue=self.queue_name).inc()
