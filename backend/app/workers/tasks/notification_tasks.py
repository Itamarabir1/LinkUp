import logging
from typing import Dict, Any
from uuid import UUID
from app.db.session import SessionLocal
from app.domain.notifications.core.handler import notification_handler
from app.domain.notifications.services.reminder_scheduler import reminder_scheduler
from app.domain.rides.crud import crud_ride
from app.domain.passengers.crud import crud_passenger
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking

from app.domain.notifications.constants import (
    NotificationEvent,
)  # re-export for backward compatibility

logger = logging.getLogger(__name__)


async def handle_ride_created(db, data: Dict[str, Any]) -> None:
    """
    אירוע ride.created: טוען נסיעה, מוצא נוסעים רלוונטיים, שולח לכל אחד מייל (ride.created_for_passengers).
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
        "ride.created: processing ride_id=%s, driver_id=%s, origin=%s, dest=%s, route_coords=%s",
        ride_id,
        getattr(ride, "driver_id", None),
        getattr(ride, "origin_name", None),
        getattr(ride, "destination_name", None),
        "exists" if getattr(ride, "route_coords", None) else "missing",
    )
    passengers = await db.run_sync(
        lambda sess: crud_passenger.find_passengers_for_ride_notification(sess, ride)
    )
    logger.info(
        "ride.created: found %d matching passengers for ride_id=%s",
        len(passengers),
        ride_id,
    )
    for pr in passengers:
        try:
            await notification_handler.handle_event(
                db,
                event_name=NotificationEvent.RIDE_CREATED_FOR_PASSENGERS.value,
                payload={"ride_id": str(ride_id), "passenger_id": str(pr.passenger_id)},
            )
        except Exception as e:
            logger.warning(
                "Failed to send ride.created_for_passengers to passenger %s: %s",
                pr.passenger_id,
                e,
            )
    logger.info(
        "ride.created: sent %d passenger notifications for ride_id=%s",
        len(passengers),
        ride_id,
    )


async def handle_ride_cancelled_by_driver(db, data: Dict[str, Any]) -> None:
    """
    אירוע ride.cancelled_by_driver: טוען הזמנות של הנסיעה, שולח לכל נוסע מייל+פוש (ride.cancelled_by_driver).
    """
    ride_id_raw = data.get("ride_id")
    if not ride_id_raw:
        logger.warning("ride.cancelled_by_driver without ride_id in payload")
        return
    ride_id = UUID(str(ride_id_raw))

    def _find_bookings(sess):
        # מחפש את כל ה-bookings של הנסיעה (כולל CANCELLED, CONFIRMED, PENDING)
        return sess.query(Booking).filter(Booking.ride_id == ride_id).all()

    bookings = await db.run_sync(_find_bookings)

    # מסנן רק bookings שהיו פעילים (CONFIRMED או PENDING) לפני הביטול
    # או CANCELLED (כי אחרי הביטול כל ה-bookings מקבלים סטטוס CANCELLED)
    active_bookings = [
        b
        for b in bookings
        if b.status
        in (
            BookingStatus.CANCELLED.value,
            BookingStatus.CONFIRMED.value,
            BookingStatus.PENDING.value,
        )
    ]

    if not active_bookings:
        logger.warning(
            "ride.cancelled_by_driver: no active bookings found for ride_id=%s", ride_id
        )
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
                "Failed to send ride.cancelled_by_driver to passenger %s: %s",
                b.passenger_id,
                e,
            )
    logger.info(
        "ride.cancelled_by_driver: sent %d passenger notifications for ride_id=%s",
        len(active_bookings),
        ride_id,
    )


async def handle_notification_event(
    data: Dict[str, Any], routing_key: str, handler=notification_handler
):
    """
    ה-Callback שמופעל ע"י ה-RabbitMQConsumer.
    routing_key הוא השם של האירוע שמגיע מרביט (למשל 'ride.created', 'ride.created_for_passengers')
    """
    logger.info(
        "[NOTIF] Consumer: handling routing_key=%s booking_id=%s",
        routing_key,
        data.get("booking_id") if isinstance(data, dict) else "?",
    )
    async with SessionLocal() as db:
        try:
            if routing_key == "ride.created":
                await handle_ride_created(db, data)
            elif routing_key == "ride.cancelled_by_driver":
                await handle_ride_cancelled_by_driver(db, data)
            else:
                await handler.handle_event(db, event_name=routing_key, payload=data)
            await db.commit()
            logger.info(
                "[NOTIF] Consumer: handler done for routing_key=%s", routing_key
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                "[NOTIF] Consumer: ERROR routing_key=%s: %s",
                routing_key,
                e,
                exc_info=True,
            )
            raise


async def execute_reminders_job(service=reminder_scheduler):
    """
    ביצוע batch תזכורות (נקרא מה-consumer של התור המתוזמן).
    """
    logger.info("⏰ Scheduler: Triggering reminder batch...")
    async with SessionLocal() as db:
        await service.run_batch_reminders(db)
