"""
notification_tasks.py — handlers לאירועי RabbitMQ + ביצוע תזכורות.

שינויים מהגרסה הקודמת:
  - handle_ride_created: כעת גם כותב scheduled_notification לנהג (driver_reminder).
  - handle_booking_approved: handler חדש — כותב scheduled_notification לנוסע (passenger_reminder).
  - execute_reminders_job: עדיין קורא ל-reminder_scheduler, שעכשיו סורק scheduled_notifications.
"""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.notifications.constants import NotificationEvent
from app.domain.notifications.core.handler import notification_handler
from app.domain.notifications.services.reminder_scheduler import reminder_scheduler
from app.domain.passengers.crud import crud_passenger
from app.domain.rides.crud import crud_ride
from app.domain.scheduled_notifications.crud import crud_scheduled_notification
from app.domain.scheduled_notifications.model import ScheduledNotificationType

logger = logging.getLogger(__name__)

# כמה זמן לפני היציאה לשלוח תזכורת
REMINDER_OFFSET = timedelta(minutes=30)


async def handle_ride_created(db, data: dict[str, Any]) -> None:
    """
    אירוע ride.created:
      1. שולח מייל לנוסעים רלוונטיים (כמקודם).
      2. כותב scheduled_notification לנהג — תזכורת 30 דקות לפני היציאה.
    """
    ride_id_raw = data.get("ride_id")
    if not ride_id_raw:
        logger.warning("ride.created without ride_id in payload")
        return
    ride_id = UUID(str(ride_id_raw))

    ride = await crud_ride.get_async(db, ride_id)
    if not ride:
        logger.warning("ride.created: ride_id=%s not found", ride_id)
        return

    logger.info(
        "ride.created: processing ride_id=%s driver_id=%s",
        ride_id,
        getattr(ride, "driver_id", None),
    )

    # 1. שליחת מייל לנוסעים רלוונטיים
    passengers = await crud_passenger.find_passengers_for_ride_notification(db, ride)
    for pr in passengers:
        try:
            await notification_handler.handle_event(
                db,
                event_name=NotificationEvent.RIDE_CREATED_FOR_PASSENGERS.value,
                payload={"ride_id": str(ride_id), "passenger_id": str(pr.passenger_id)},
            )
        except Exception as e:
            logger.warning(
                "ride.created: failed to notify passenger %s: %s",
                pr.passenger_id,
                e,
            )

    # 2. תזכורת לנהג — 30 דקות לפני departure_time
    if ride.departure_time:
        deliver_at = ride.departure_time - REMINDER_OFFSET
        await crud_scheduled_notification.create(
            db,
            ride_id=ride_id,
            user_id=ride.driver_id,
            type=ScheduledNotificationType.DRIVER_REMINDER,
            deliver_at=deliver_at,
        )
        logger.info(
            "ride.created: scheduled driver reminder ride_id=%s deliver_at=%s",
            ride_id,
            deliver_at,
        )

    logger.info(
        "ride.created: done ride_id=%s passengers_notified=%d",
        ride_id,
        len(passengers),
    )


async def handle_booking_approved(db, data: dict[str, Any]) -> None:
    """
    אירוע booking.approved_by_driver:
      1. שולח מייל+פוש לנוסע (כמקודם, דרך notification_handler).
      2. כותב scheduled_notification לנוסע — תזכורת 30 דקות לפני האיסוף.
    """
    booking_id_raw = data.get("booking_id")
    if not booking_id_raw:
        logger.warning("booking.approved_by_driver without booking_id in payload")
        return
    booking_id = UUID(str(booking_id_raw))

    booking = await crud_booking.get_booking_by_id_async(db, booking_id)
    if not booking:
        logger.warning("booking.approved_by_driver: booking_id=%s not found", booking_id)
        return

    # 1. מייל+פוש לנוסע
    try:
        await notification_handler.handle_event(
            db,
            event_name=NotificationEvent.BOOKING_APPROVED_BY_DRIVER.value,
            payload={"booking_id": str(booking_id)},
        )
    except Exception as e:
        logger.warning(
            "booking.approved_by_driver: failed to notify passenger %s: %s",
            booking.passenger_id,
            e,
        )

    # 2. תזכורת לנוסע — 30 דקות לפני pickup_time (אם קיים), אחרת departure_time
    ride = booking.ride
    pickup_time = booking.pickup_time or (ride.departure_time if ride else None)
    if pickup_time:
        deliver_at = pickup_time - REMINDER_OFFSET
        await crud_scheduled_notification.create(
            db,
            ride_id=booking.ride_id,
            user_id=booking.passenger_id,
            type=ScheduledNotificationType.PASSENGER_REMINDER,
            deliver_at=deliver_at,
        )
        logger.info(
            "booking.approved_by_driver: scheduled passenger reminder booking_id=%s deliver_at=%s",
            booking_id,
            deliver_at,
        )


async def handle_ride_cancelled_by_driver(db, data: dict[str, Any]) -> None:
    """
    אירוע ride.cancelled_by_driver:
    שולח מייל+פוש לכל נוסע שהיה בנסיעה.
    ON DELETE CASCADE מטפל אוטומטית במחיקת scheduled_notifications של הנסיעה.
    """
    ride_id_raw = data.get("ride_id")
    if not ride_id_raw:
        logger.warning("ride.cancelled_by_driver without ride_id in payload")
        return
    ride_id = UUID(str(ride_id_raw))

    result = await db.execute(select(Booking).where(Booking.ride_id == ride_id))
    bookings = list(result.scalars().all())
    active_bookings = [
        b
        for b in bookings
        if b.status
        in (
            BookingStatus.CONFIRMED.value,
            BookingStatus.PENDING.value,
        )
    ]

    if not active_bookings:
        logger.warning("ride.cancelled_by_driver: no active bookings for ride_id=%s", ride_id)
        return

    for b in active_bookings:
        try:
            await notification_handler.handle_event(
                db,
                event_name=NotificationEvent.RIDE_CANCELLED_BY_DRIVER.value,
                payload={"ride_id": str(ride_id), "passenger_id": str(b.passenger_id)},
            )
        except Exception as e:
            logger.warning(
                "ride.cancelled_by_driver: failed to notify passenger %s: %s",
                b.passenger_id,
                e,
            )

    logger.info(
        "ride.cancelled_by_driver: notified %d passengers for ride_id=%s",
        len(active_bookings),
        ride_id,
    )


async def handle_notification_event(
    data: dict[str, Any],
    routing_key: str,
    handler=notification_handler,
) -> None:
    """
    Callback של ה-RabbitMQ consumer.
    routing_key מתאים ל-NotificationEvent values.
    """
    logger.info(
        "[NOTIF] Consumer: routing_key=%s",
        routing_key,
    )
    async with SessionLocal() as db:
        try:
            if routing_key == NotificationEvent.RIDE_CANCELLED_BY_DRIVER.value:
                await handle_ride_cancelled_by_driver(db, data)
            elif routing_key == "ride.created":
                await handle_ride_created(db, data)
            elif routing_key == NotificationEvent.BOOKING_APPROVED_BY_DRIVER.value:
                await handle_booking_approved(db, data)
            else:
                await handler.handle_event(db, event_name=routing_key, payload=data)
            await db.commit()
            logger.info("[NOTIF] Consumer: done routing_key=%s", routing_key)
        except Exception as e:
            await db.rollback()
            logger.error(
                "[NOTIF] Consumer: ERROR routing_key=%s: %s",
                routing_key,
                e,
                exc_info=True,
            )
            raise


async def execute_reminders_job(service=reminder_scheduler) -> None:
    """
    ביצוע batch תזכורות — נקרא מה-scheduler כל 5 דקות.
    reminder_scheduler סורק scheduled_notifications במקום rides/bookings.
    """
    logger.info("⏰ Scheduler: Triggering reminder batch...")
    async with SessionLocal() as db:
        await service.run_batch_reminders(db)
