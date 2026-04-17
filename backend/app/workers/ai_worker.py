import asyncio
import logging
import signal
import sys

# Import models before ORM resolves string relationships
import app.db.models  # noqa: F401
from app.core.logging import setup_logging
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.workers.tasks.chat_summary_task import run_chat_completion_redis_listener

setup_logging()
logger = logging.getLogger("AIWorker")


async def main():
    logger.info("Starting AI worker...")

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

    chat_pubsub_ok = False
    try:
        await redis_chat_pubsub.connect()
        chat_pubsub_ok = True

        tasks = [
            asyncio.create_task(run_chat_completion_redis_listener(stop_event)),
        ]
        logger.info("AI worker tasks running: %s", len(tasks))
        await stop_event.wait()

    except (KeyboardInterrupt, SystemExit):
        logger.info("Keyboard interrupt received.")
        stop_handler()
    except Exception as e:
        logger.error("Critical AI worker error: %s", e, exc_info=True)
    finally:
        logger.info("Shutting down AI worker...")
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=5)
        if chat_pubsub_ok:
            try:
                await redis_chat_pubsub.close()
            except Exception as e:
                logger.warning("redis_chat_pubsub.close failed: %s", e)
        logger.info("AI worker shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
