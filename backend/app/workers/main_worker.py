import asyncio
import logging
import signal
import sys

# רישום כל המודלים לפני שימוש ב-ORM (מניעת "expression 'Group' failed to locate a name")
import app.db.models  # noqa: F401

# Firebase Admin SDK init (side-effect import; safe idempotent)
import app.infrastructure.firebase_core.firebase  # noqa: F401
from app.core.logging import setup_logging
from app.domain.events.routing import (
    AVATAR_UPLOAD_EXCHANGES,
    NOTIFICATION_EXCHANGES,
    SCHEDULED_EXCHANGES,
    SCHEDULED_TASKS_QUEUE,
)
from app.infrastructure.events.dispatcher.factory import DispatcherFactory
from app.infrastructure.events.publishers.rabbitmq import RabbitMQPublisher

# Infrastructure
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub

# Workers & Tasks
from app.workers.outbox_worker import run_outbox_worker
from app.workers.tasks.avatar_tasks import handle_avatar_upload_event
from app.workers.tasks.chat_summary_task import run_chat_completion_redis_listener
from app.workers.tasks.notification_tasks import handle_notification_event
from app.workers.tasks.scheduled_tasks import (
    handle_scheduled_task,
    run_scheduled_tasks_publisher,
)

setup_logging()
logger = logging.getLogger("WorkerMain")


async def main():
    logger.info("🚀 Linkup Worker Engine is starting...")

    # 1. ניהול Graceful Shutdown - הגדרה מוקדמת
    stop_event = asyncio.Event()
    tasks = []

    def stop_handler():
        """פונקציה שתקרא בזמן פקודת עצירה"""
        logger.info("🛑 Shutdown signal received. Signalizing tasks to stop...")
        stop_event.set()

    # טיפול בסיגנלים - שבירת המוקש של Windows
    if sys.platform != "win32":
        # לינוקס / מאק תומכים ב-add_signal_handler
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_handler)
    else:
        # ב-Windows אנחנו נסמוך על KeyboardInterrupt בתוך ה-try
        logger.info("ℹ️ Windows detected: Using standard interrupt handling.")

    broadcast_ok = False
    chat_pubsub_ok = False
    try:
        # 2. אתחול תשתיות
        await rabbit_client.connect()
        try:
            await broadcast.connect()
            broadcast_ok = True
            logger.info("✅ [Worker] Redis Broadcast connected (in-app notifications)")
        except Exception as e:
            logger.warning(
                "⚠️ [Worker] Redis Broadcast unavailable (WS notifications disabled): %s",
                e,
            )

        try:
            await redis_chat_pubsub.connect()
            chat_pubsub_ok = True
            logger.info("✅ [Worker] Redis Chat Pub/Sub connected")
        except Exception as e:
            logger.warning("⚠️ [Worker] Redis Chat Pub/Sub unavailable: %s", e)

        # 3. הזרקת תלויות (Dependency Injection)
        rmq_publisher = RabbitMQPublisher(rabbit_client=rabbit_client)
        dispatcher = DispatcherFactory.create_standard_dispatcher(publishers=[rmq_publisher])

        notifications_consumer = RabbitMQConsumer(
            rabbit_client,
            queue_name="notifications_queue",
            exchange_names=NOTIFICATION_EXCHANGES,
        )
        avatar_upload_consumer = RabbitMQConsumer(
            rabbit_client,
            queue_name="avatar_upload_queue",
            exchange_names=AVATAR_UPLOAD_EXCHANGES,
        )
        scheduled_tasks_consumer = RabbitMQConsumer(
            rabbit_client,
            queue_name=SCHEDULED_TASKS_QUEUE,
            exchange_names=SCHEDULED_EXCHANGES,
        )

        # 4. הגדרת המשימות כ-Tasks עצמאיים (כולל משימות מתוזמנות דרך התור)
        tasks = [
            asyncio.create_task(notifications_consumer.consume(callback=handle_notification_event)),
            asyncio.create_task(avatar_upload_consumer.consume(callback=handle_avatar_upload_event)),
            asyncio.create_task(scheduled_tasks_consumer.consume(callback=handle_scheduled_task)),
            asyncio.create_task(run_scheduled_tasks_publisher()),
            asyncio.create_task(run_outbox_worker(dispatcher=dispatcher)),
            asyncio.create_task(run_chat_completion_redis_listener(stop_event)),
        ]

        logger.info(f"✅ All {len(tasks)} workers are running. Press Ctrl+C to stop.")

        # 5. המתנה לסיום - או שמישהו סימן עצירה, או שאחת המשימות קרסה
        stop_task = asyncio.create_task(stop_event.wait())

        # אנחנו מחכים ש-stop_event יופעל (ע"י ה-handler או ה-except)
        await stop_task

    except (KeyboardInterrupt, SystemExit):
        # תופס Ctrl+C ב-Windows
        logger.info("⌨️ Keyboard Interrupt received.")
        stop_handler()
    except Exception as e:
        logger.error(f"❌ Critical error during worker startup: {e}", exc_info=True)

    finally:
        # 6. ניקוי (Graceful Cleanup)
        logger.info("👋 Shutting down: Cancelling all tasks...")

        for t in tasks:
            if not t.done():
                t.cancel()

        if tasks:
            # המתנה של מקסימום 5 שניות לסגירת המשימות
            await asyncio.wait(tasks, timeout=5)

        if broadcast_ok:
            try:
                await broadcast.disconnect()
            except Exception as e:
                logger.warning("⚠️ [Worker] broadcast.disconnect: %s", e)
        if chat_pubsub_ok:
            try:
                await redis_chat_pubsub.close()
            except Exception as e:
                logger.warning("⚠️ [Worker] redis_chat_pubsub.close: %s", e)
        await rabbit_client.close()
        logger.info("🏁 Linkup Worker Engine shut down cleanly.")


if __name__ == "__main__":
    # שימוש ב-run בצורה בטוחה
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # מונע הדפסת Traceback מכוער כשסוגרים את הטרמינל
        pass
