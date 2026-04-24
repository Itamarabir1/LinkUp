import asyncio
import logging
import signal
import sys

# Import models before ORM resolves string relationships
import app.db.models  # noqa: F401

# Firebase Admin SDK init (side-effect import; safe idempotent)
import app.infrastructure.firebase_core.firebase  # noqa: F401
from app.core.logging import setup_logging
from app.domain.events.routing import NOTIFICATION_EXCHANGES
from app.infrastructure.events.dispatcher.factory import DispatcherFactory
from app.infrastructure.events.publishers.rabbitmq import RabbitMQPublisher
from app.infrastructure.rabbitmq.client import outbox_rabbit_client, worker_rabbit_client
from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from app.infrastructure.rabbitmq.dlq_monitor import run_dlq_monitor
from app.infrastructure.rabbitmq.supervisor import run_supervised
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.workers.outbox_worker import run_outbox_worker
from app.workers.tasks.notification_tasks import handle_notification_event
from prometheus_client import start_http_server

setup_logging()
logger = logging.getLogger("NotificationWorker")


async def main():
    logger.info("Starting notification worker...")

    stop_event = asyncio.Event()
    tasks = []

    def stop_handler():
        logger.info("Shutdown signal received. Signaling tasks to stop...")
        stop_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_handler)
    else:
        logger.info("Windows detected: using KeyboardInterrupt handling.")

    broadcast_ok = False
    chat_pubsub_ok = False
    worker_rmq_ok = False
    outbox_rmq_ok = False
    try:
        await worker_rabbit_client.connect()
        worker_rmq_ok = True
        await outbox_rabbit_client.connect()
        outbox_rmq_ok = True
        try:
            await broadcast.connect()
            broadcast_ok = True
        except Exception as e:
            logger.warning("Broadcast unavailable: %s", e)

        try:
            await redis_chat_pubsub.connect()
            chat_pubsub_ok = True
        except Exception as e:
            logger.warning("Redis chat pubsub unavailable: %s", e)

        rmq_publisher = RabbitMQPublisher(rabbit_client=outbox_rabbit_client)
        dispatcher = DispatcherFactory.create_standard_dispatcher(publishers=[rmq_publisher])

        notifications_consumer = RabbitMQConsumer(
            worker_rabbit_client,
            queue_name="notifications_queue",
            exchange_names=NOTIFICATION_EXCHANGES,
        )

        tasks = [
            asyncio.create_task(
                run_supervised(
                    "notifications-consumer",
                    lambda: notifications_consumer.consume(callback=handle_notification_event, stop_event=stop_event),
                    stop_event,
                )
            ),
            asyncio.create_task(
                run_supervised(
                    "outbox-worker",
                    lambda: run_outbox_worker(dispatcher=dispatcher),
                    stop_event,
                )
            ),
            asyncio.create_task(
                run_supervised(
                    "dlq-monitor",
                    lambda: run_dlq_monitor(worker_rabbit_client, stop_event),
                    stop_event,
                )
            ),
        ]

        logger.info("Notification worker tasks running: %s", len(tasks))
        start_http_server(9091)
        await stop_event.wait()

    except (KeyboardInterrupt, SystemExit):
        logger.info("Keyboard interrupt received.")
        stop_handler()
    except Exception as e:
        logger.error("Critical notification worker error: %s", e, exc_info=True)
    finally:
        logger.info("Shutting down notification worker...")
        stop_event.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=30)

        if broadcast_ok:
            try:
                await broadcast.disconnect()
            except Exception as e:
                logger.warning("broadcast.disconnect failed: %s", e)
        if chat_pubsub_ok:
            try:
                await redis_chat_pubsub.close()
            except Exception as e:
                logger.warning("redis_chat_pubsub.close failed: %s", e)
        if outbox_rmq_ok:
            await outbox_rabbit_client.close()
        if worker_rmq_ok:
            await worker_rabbit_client.close()
        logger.info("Notification worker shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
