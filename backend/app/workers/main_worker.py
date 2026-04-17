"""
DEPRECATED: main_worker.py is kept for backward compatibility.
Use notification_worker, task_worker, or ai_worker instead.
"""

import asyncio
import logging

from app.core.logging import setup_logging
from app.workers.notification_worker import main as notification_main

setup_logging()
logger = logging.getLogger("MainWorker")


async def main():
    logger.warning(
        "main_worker.py is deprecated. "
        "Use notification_worker, task_worker, or ai_worker. "
        "Running notification_worker for backward compatibility."
    )
    await notification_main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
