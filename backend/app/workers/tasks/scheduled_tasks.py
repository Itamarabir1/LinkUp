"""
Scheduled tasks via the queue.
Publisher sends messages to RabbitMQ; consumer pulls and runs handlers.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from app.domain.events.routing import (
    ROUTING_KEY_CHAT_TIMEOUT,
    ROUTING_KEY_FUEL_SCAN,
    ROUTING_KEY_MAINTENANCE,
    ROUTING_KEY_REMINDERS,
    SCHEDULED_EXCHANGE,
)
from app.infrastructure.rabbitmq.client import rabbit_client
from app.workers.tasks.chat_timeout_task import execute_chat_timeout_job
from app.workers.tasks.fuel_price_task import FUEL_SCAN_INTERVAL, execute_fuel_scan_job
from app.workers.tasks.maintenance_task import execute_maintenance_job
from app.workers.tasks.notification_tasks import execute_reminders_job

logger = logging.getLogger(__name__)

# Intervals (seconds) — when to publish to the queue
INTERVAL_MAINTENANCE = 1500
INTERVAL_REMINDERS = 300
INTERVAL_CHAT_TIMEOUT = 3600
CHECK_INTERVAL = 60  # wake every minute


async def run_scheduled_tasks_publisher():
    """
    Publisher: sends to the "scheduled" exchange every N seconds.
    Does not run business logic — only publishes; the consumer runs jobs.
    """
    last_fuel = last_maintenance = last_reminders = last_chat_timeout = time.monotonic()
    logger.info("📅 Scheduled tasks publisher started")

    while True:
        try:
            now = time.monotonic()
            if now - last_chat_timeout >= INTERVAL_CHAT_TIMEOUT:
                await rabbit_client.publish(
                    {"trigger": "chat_timeout"},
                    ROUTING_KEY_CHAT_TIMEOUT,
                    SCHEDULED_EXCHANGE,
                )
                last_chat_timeout = now
                logger.debug("📤 Published scheduled.chat_timeout")
            if now - last_reminders >= INTERVAL_REMINDERS:
                await rabbit_client.publish(
                    {"trigger": "reminders"},
                    ROUTING_KEY_REMINDERS,
                    SCHEDULED_EXCHANGE,
                )
                last_reminders = now
                logger.debug("📤 Published scheduled.reminders")
            if now - last_maintenance >= INTERVAL_MAINTENANCE:
                await rabbit_client.publish(
                    {"trigger": "maintenance"},
                    ROUTING_KEY_MAINTENANCE,
                    SCHEDULED_EXCHANGE,
                )
                last_maintenance = now
                logger.debug("📤 Published scheduled.maintenance")
            if now - last_fuel >= FUEL_SCAN_INTERVAL:
                await rabbit_client.publish(
                    {"trigger": "fuel_scan"},
                    ROUTING_KEY_FUEL_SCAN,
                    SCHEDULED_EXCHANGE,
                )
                last_fuel = now
                logger.debug("📤 Published scheduled.fuel_scan")
        except Exception as e:
            logger.error("❌ Scheduled publisher failed: %s", e, exc_info=True)

        await asyncio.sleep(CHECK_INTERVAL)


async def handle_scheduled_task(data: dict[str, Any], routing_key: str) -> None:
    """
    Consumer callback for scheduled_tasks_queue.
    Dispatches to the matching execute_* by routing_key.
    """
    try:
        if routing_key == ROUTING_KEY_FUEL_SCAN:
            await execute_fuel_scan_job()
        elif routing_key == ROUTING_KEY_MAINTENANCE:
            await execute_maintenance_job()
        elif routing_key == ROUTING_KEY_REMINDERS:
            await execute_reminders_job()
        elif routing_key == ROUTING_KEY_CHAT_TIMEOUT:
            await execute_chat_timeout_job()
        else:
            logger.warning("⚠️ Unknown scheduled task routing_key: %s", routing_key)
    except Exception as e:
        logger.error(
            "Scheduled task failed — will retry on next schedule",
            extra={
                "task_type": routing_key,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            },
            exc_info=True,
        )
        # Do not raise: scheduled tasks are periodic; requeue can infinite-loop (poison message).
        # Fail once, log, and the publisher will fire again on the next tick.
        return
