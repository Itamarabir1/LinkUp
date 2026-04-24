import asyncio
import logging

from app.infrastructure.rabbitmq.topology import QUEUE_SPECS

logger = logging.getLogger(__name__)

DLQ_MONITOR_INTERVAL_SECONDS = 60
DLQ_WARNING_THRESHOLD = 10
DLQ_CRITICAL_THRESHOLD = 50


def _retryable_dlq_names() -> list[str]:
    return [f"{spec.queue_name}.dlq" for spec in QUEUE_SPECS.values() if spec.retry_enabled]


def _queue_message_count(queue: object) -> int:
    declaration_result = getattr(queue, "declaration_result", None)
    message_count = getattr(declaration_result, "message_count", 0) if declaration_result else 0
    try:
        return int(message_count)
    except (TypeError, ValueError):
        return 0


async def run_dlq_monitor(rabbit_client, stop_event: asyncio.Event) -> None:
    """
    Periodically checks DLQ depth and emits threshold-based alerts.
    """
    dlq_names = _retryable_dlq_names()
    if not dlq_names:
        logger.info("DLQ monitor disabled: no retry-enabled queues registered")
        await stop_event.wait()
        return

    logger.info(
        "DLQ monitor started interval=%ss warning=%s critical=%s queues=%s",
        DLQ_MONITOR_INTERVAL_SECONDS,
        DLQ_WARNING_THRESHOLD,
        DLQ_CRITICAL_THRESHOLD,
        dlq_names,
    )

    while not stop_event.is_set():
        try:
            channel = await rabbit_client.get_consumer_channel("dlq-monitor")
            for queue_name in dlq_names:
                queue = await channel.declare_queue(queue_name, durable=True, passive=True)
                depth = _queue_message_count(queue)
                if depth >= DLQ_CRITICAL_THRESHOLD:
                    logger.critical("DLQ depth critical queue=%s depth=%s", queue_name, depth)
                elif depth >= DLQ_WARNING_THRESHOLD:
                    logger.warning("DLQ depth warning queue=%s depth=%s", queue_name, depth)
                else:
                    logger.info("DLQ depth healthy queue=%s depth=%s", queue_name, depth)
        except Exception as e:
            logger.error("DLQ monitor failed: %s", e, exc_info=True)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=DLQ_MONITOR_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue
