import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

# 1. דאטה ו-CRUD (כדי למשוך את הנסיעות וההזמנות שצריכות תזכורת)
from app.domain.rides.crud import crud_ride
from app.domain.bookings.crud import crud_booking

# 2. ה-Handler של מערכת הנוטיפיקציות (המוח העסקי)
from app.domain.notifications.core.handler import notification_handler

logger = logging.getLogger(__name__)


class ReminderScheduler:
    async def run_batch_reminders(self, db: AsyncSession):
        """
        השם שונה ל-run_batch כי זה תהליך אצווה (Batch) שרץ מדי כמה דקות.
        """
        now = datetime.now(timezone.utc)
        # חלון זמן של 30 דקות קדימה
        start_w, end_w = now + timedelta(minutes=25), now + timedelta(minutes=35)

        logger.info(f"⏳ Starting reminder batch for window: {start_w} - {end_w}")

        await self._remind_passengers(db, start_w, end_w)
        await self._remind_drivers(db, start_w, end_w)

    async def _remind_passengers(self, db: AsyncSession, start: datetime, end: datetime):
        # השם שונה מ-handle ל-remind כדי להבהיר מה הפעולה העסקית
        bookings = await crud_booking.get_bookings_for_reminders(db, start, end)
        if not bookings:
            return

        for booking in bookings:
            try:
                await notification_handler.handle_event(
                    db,
                    event_name="PICKUP_REMINDER_PASSENGER",
                    payload={"booking_id": booking.booking_id},
                )
                booking.reminder_sent = True
                await db.flush()
            except Exception as e:
                logger.error(
                    "Failed passenger reminder %s: %s",
                    booking.booking_id,
                    e,
                    exc_info=True,
                )

        await self._safe_commit(db, "Passenger Reminders")

    async def _remind_drivers(self, db: AsyncSession, start: datetime, end: datetime):
        # 1. הוספת await - עכשיו rides תהיה רשימה אמיתית
        rides = await crud_ride.get_rides_needing_reminders(db, start, end)

        if not rides:
            return

        for ride in rides:
            try:
                await notification_handler.handle_event(
                    db,
                    event_name="RIDE_START_DRIVER",
                    payload={"ride_id": ride.ride_id},
                )

                # 3. עדכון הסטטוס
                ride.reminder_sent = True

                # 4. ביצוע Flush אסינכרוני כדי "לדחוף" את השינוי ל-DB בתוך הטרנזקציה
                await db.flush()

            except Exception as e:
                logger.error(
                    "Failed driver reminder %s: %s",
                    ride.ride_id,
                    e,
                    exc_info=True,
                )

        # 5. ביצוע Commit סופי
        await self._safe_commit(db, "Driver Reminders")

    async def _safe_commit(self, db: AsyncSession, context: str):
        try:
            await db.commit()
            logger.info(f"✅ Committed {context}")
        except Exception as e:
            await db.rollback()
            logger.critical("Database error in %s: %s", context, e, exc_info=True)


# המופע שייובא ב-Celery/Cron task
reminder_scheduler = ReminderScheduler()
