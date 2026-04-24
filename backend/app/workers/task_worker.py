import asyncio
import logging
import signal
import sys

# Import models before ORM resolves string relationships
import app.db.models  # noqa: F401
from app.core.logging import setup_logging
from app.domain.events.routing import (
    AVATAR_UPLOAD_EXCHANGES,
    SCHEDULED_EXCHANGES,
    SCHEDULED_TASKS_QUEUE,
)
from app.infrastructure.rabbitmq.client import worker_rabbit_client
from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from app.infrastructure.rabbitmq.supervisor import run_supervised
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.infrastructure.redis.client import redis_client
from app.workers.tasks.avatar_tasks import handle_avatar_upload_event
from app.workers.tasks.scheduled_tasks import (
    handle_scheduled_task,
    run_scheduled_tasks_publisher,
)
from prometheus_client import start_http_server

setup_logging()
logger = logging.getLogger("TaskWorker")


async def main():
    logger.info("Starting task worker...")

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
    redis_client_ok = False
    worker_rmq_ok = False
    try:
        await worker_rabbit_client.connect()
        worker_rmq_ok = True
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
        try:
            await redis_client.connect()
            redis_client_ok = True
        except Exception as e:
            logger.warning("Redis cache client unavailable: %s", e)

        avatar_upload_consumer = RabbitMQConsumer(
            worker_rabbit_client,
            queue_name="avatar_upload_queue",
            exchange_names=AVATAR_UPLOAD_EXCHANGES,
        )
        scheduled_tasks_consumer = RabbitMQConsumer(
            worker_rabbit_client,
            queue_name=SCHEDULED_TASKS_QUEUE,
            exchange_names=SCHEDULED_EXCHANGES,
        )

        tasks = [
            asyncio.create_task(
                run_supervised(
                    "avatar-upload-consumer",
                    lambda: avatar_upload_consumer.consume(callback=handle_avatar_upload_event, stop_event=stop_event),
                    stop_event,
                )
            ),
            asyncio.create_task(
                run_supervised(
                    "scheduled-tasks-consumer",
                    lambda: scheduled_tasks_consumer.consume(callback=handle_scheduled_task, stop_event=stop_event),
                    stop_event,
                )
            ),
            asyncio.create_task(
                run_supervised(
                    "scheduled-tasks-publisher",
                    lambda: run_scheduled_tasks_publisher(worker_rabbit_client),
                    stop_event,
                )
            ),
        ]
        logger.info("Task worker tasks running: %s", len(tasks))
        start_http_server(9092)
        await stop_event.wait()

    except (KeyboardInterrupt, SystemExit):
        logger.info("Keyboard interrupt received.")
        stop_handler()
    except Exception as e:
        logger.error("Critical task worker error: %s", e, exc_info=True)
    finally:
        logger.info("Shutting down task worker...")
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
        if redis_client_ok:
            try:
                await redis_client.close()
            except Exception as e:
                logger.warning("redis_client.close failed: %s", e)
        if worker_rmq_ok:
            await worker_rabbit_client.close()
        logger.info("Task worker shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
