import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)


async def run_supervised(
    name: str,
    worker_factory: Callable[[], Awaitable[Any]],
    stop_event: asyncio.Event,
    base_backoff_seconds: float = 1.0,
    max_backoff_seconds: float = 30.0,
    max_retries: int = 5,
) -> None:
    """
    Runs a long-lived worker coroutine with restart-on-failure policy.
    Used by worker entrypoints to avoid silent task death.
    """
    attempt = 0
    while not stop_event.is_set():
        try:
            await worker_factory()
            if stop_event.is_set():
                return
            logger.warning("Supervised task exited unexpectedly: %s", name)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Supervised task crashed: %s error=%s", name, e, exc_info=True)

        attempt += 1
        if attempt >= max_retries:
            logger.critical("Task %s failed %s times, stopping", name, attempt)
            stop_event.set()
            return
        backoff = min(max_backoff_seconds, base_backoff_seconds * (2 ** min(attempt, 6)))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=backoff)
            return
        except asyncio.TimeoutError:
            continue
