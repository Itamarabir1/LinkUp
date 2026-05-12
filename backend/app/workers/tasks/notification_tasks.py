"""
notification_tasks.py — RabbitMQ event handlers + reminder execution.

Changes from the previous version:
  - handle_ride_created: also writes driver scheduled_notification (driver_reminder).
  - handle_booking_approved: new handler — writes passenger scheduled_notification (passenger_reminder).
  - execute_reminders_job: still calls reminder_scheduler, which now scans scheduled_notifications.
"""

import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.notifications.constants import NotificationEvent
from app.domain.notifications.core.handler import notification_handler
from app.domain.notifications.manager import NotificationCommand, notification_manager
from app.domain.notifications.services.reminder_scheduler import reminder_scheduler
from app.domain.passengers.crud import crud_passenger
from app.domain.rides.crud import crud_ride
from app.domain.scheduled_notifications.crud import crud_scheduled_notification
from app.domain.scheduled_notifications.model import ScheduledNotificationType
from app.domain.users.crud import crud_user
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub

logger = logging.getLogger(__name__)

CHAT_PUSH_DEBOUNCE_TTL = 30

# How long before departure to send a reminder
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

    # 1. Email relevant passengers
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

    # 2. Driver reminder — 30 minutes before departure_time
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
    booking.approved_by_driver event:
      1. Email+push to passenger (via notification_handler, as before).
      2. Write passenger scheduled_notification — reminder 30 minutes before pickup.
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

    # 1. Email+push to passenger
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

    # 2. Passenger reminder — 30 minutes before pickup_time if set, else departure_time
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
    ride.cancelled_by_driver event:
    Sends email+push to every passenger on the ride.
    ON DELETE CASCADE removes scheduled_notifications for the ride automatically.
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


async def _is_user_online(user_id: str) -> bool:
    """Check chat-ws presence key on Redis DB 1."""
    if redis_chat_pubsub.client is None:
        return False
    try:
        return await redis_chat_pubsub.client.exists(f"presence:{user_id}") > 0
    except Exception:
        return False


async def _claim_debounce(conversation_id: str, recipient_id: str) -> bool:
    """Claim a debounce slot (max 1 push per conversation per CHAT_PUSH_DEBOUNCE_TTL).
    Returns True if claimed, False if a recent push was already sent."""
    if redis_chat_pubsub.client is None:
        return True
    key = f"chat_push_debounce:{recipient_id}:{conversation_id}"
    try:
        return await redis_chat_pubsub.client.set(key, "1", nx=True, ex=CHAT_PUSH_DEBOUNCE_TTL)
    except Exception:
        return True


async def handle_chat_message_push(db: AsyncSession, data: dict[str, Any]) -> None:
    """Send push notification for a chat message when the recipient is offline."""
    recipient_id = data.get("recipient_id")
    sender_id = data.get("sender_id")
    conversation_id = data.get("conversation_id")
    if not recipient_id or not sender_id or not conversation_id:
        return

    if await _is_user_online(recipient_id):
        logger.debug("chat push skipped: user %s is online", recipient_id)
        return

    if not await _claim_debounce(conversation_id, recipient_id):
        logger.debug("chat push debounced: conv %s user %s", conversation_id, recipient_id)
        return

    recipient = await crud_user.get_by_id(db, recipient_id)
    sender = await crud_user.get_by_id(db, sender_id)
    if not recipient or not sender:
        return

    body_text = data.get("body", "")
    cmd = NotificationCommand(
        user=recipient,
        template="chat_message",
        channels=["push"],
        context={
            "push_title": f"הודעה מ-{sender.full_name or 'LinkUp'}",
            "push_body": body_text[:100],
            "sender_name": sender.full_name or "LinkUp",
            "message_preview": body_text[:100],
            "conversation_id": conversation_id,
            "event_key": "chat.message_sent",
        },
        event_key="chat.message_sent",
        db=db,
    )
    await notification_manager.process_and_send(cmd)
    logger.info("chat push sent: conv=%s recipient=%s", conversation_id, recipient_id)


async def handle_notification_event(
    data: dict[str, Any],
    routing_key: str,
    handler=notification_handler,
) -> None:
    """
    RabbitMQ consumer callback.
    routing_key matches NotificationEvent values.
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
            elif routing_key == "chat.message_sent":
                await handle_chat_message_push(db, data)
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
    Run reminder batch — invoked by the scheduler every few minutes.
    reminder_scheduler scans scheduled_notifications instead of rides/bookings.
    """
    logger.info("⏰ Scheduler: Triggering reminder batch...")
    async with SessionLocal() as db:
        await service.run_batch_reminders(db)
