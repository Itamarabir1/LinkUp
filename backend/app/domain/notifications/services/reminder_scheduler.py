"""
reminder_scheduler.py — sends reminders based on scheduled_notifications.

Compared to the previous version:
  Before: scanned all rides and bookings with a time window — O(n) over all rides.
  Now: scans scheduled_notifications WHERE sent_at IS NULL AND deliver_at <= now
       — O(k) over pending reminders only, thanks to a partial index.

reminder_sent was removed from Ride and Booking (migration 008).
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BATCH_SIZE_DEFAULT
from app.domain.notifications.constants import NotificationEvent
from app.domain.notifications.core.handler import notification_handler
from app.domain.scheduled_notifications.crud import crud_scheduled_notification
from app.domain.scheduled_notifications.model import ScheduledNotificationType

logger = logging.getLogger(__name__)


class ReminderScheduler:
    async def run_batch_reminders(self, db: AsyncSession) -> None:
        """
        Runs a batch of reminders that are due.
        Batch limit (BATCH_SIZE_DEFAULT) avoids overload — if there are more, the next run handles the rest.
        """
        now = datetime.now(UTC)
        due = await crud_scheduled_notification.get_due(db, now, limit=BATCH_SIZE_DEFAULT)

        if not due:
            return

        logger.info("⏰ ReminderScheduler: found %d due notifications", len(due))

        for notification in due:
            try:
                if notification.type == ScheduledNotificationType.PASSENGER_REMINDER:
                    await notification_handler.handle_event(
                        db,
                        event_name=NotificationEvent.PICKUP_REMINDER_PASSENGER.value,
                        payload={
                            "scheduled_notification_id": str(notification.id),
                            "ride_id": str(notification.ride_id) if notification.ride_id else None,
                            "user_id": str(notification.user_id),
                        },
                    )
                elif notification.type == ScheduledNotificationType.DRIVER_REMINDER:
                    await notification_handler.handle_event(
                        db,
                        event_name=NotificationEvent.RIDE_START_DRIVER.value,
                        payload={
                            "scheduled_notification_id": str(notification.id),
                            "ride_id": str(notification.ride_id) if notification.ride_id else None,
                            "user_id": str(notification.user_id),
                        },
                    )

                await crud_scheduled_notification.mark_sent(db, notification.id)
                await db.flush()

            except Exception as e:
                logger.error(
                    "ReminderScheduler: failed notification_id=%s type=%s: %s",
                    notification.id,
                    notification.type,
                    e,
                    exc_info=True,
                )
                # Continue to the next reminder — one failure does not stop the batch

        await self._safe_commit(db)

    async def _safe_commit(self, db: AsyncSession) -> None:
        try:
            await db.commit()
            logger.info("✅ ReminderScheduler: batch committed")
        except Exception as e:
            await db.rollback()
            logger.critical("ReminderScheduler: commit failed: %s", e, exc_info=True)


reminder_scheduler = ReminderScheduler()
