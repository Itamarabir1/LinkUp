"""Unit tests for notification worker tasks (RabbitMQ event handlers + reminder execution)."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.bookings.enum import BookingStatus
from app.domain.notifications.constants import NotificationEvent
from app.domain.scheduled_notifications.model import ScheduledNotificationType
from app.workers.tasks.notification_tasks import (
    REMINDER_OFFSET,
    execute_reminders_job,
    handle_booking_approved,
    handle_notification_event,
    handle_ride_cancelled_by_driver,
    handle_ride_created,
)


# ============================================================
# handle_ride_created
# ============================================================


@pytest.mark.asyncio
async def test_handle_ride_created_missing_ride_id_returns_early():
    db = AsyncMock()
    await handle_ride_created(db, {})
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_ride_created_ride_not_found_returns_early():
    db = AsyncMock()
    ride_id = uuid4()
    with patch(
        "app.workers.tasks.notification_tasks.crud_ride.get_async",
        new_callable=AsyncMock,
        return_value=None,
    ):
        await handle_ride_created(db, {"ride_id": str(ride_id)})


@pytest.mark.asyncio
async def test_handle_ride_created_notifies_passengers_and_schedules_driver_reminder():
    db = AsyncMock()
    ride_id = uuid4()
    driver_id = uuid4()
    departure = datetime(2026, 6, 1, 10, 0, 0)

    ride = MagicMock()
    ride.ride_id = ride_id
    ride.driver_id = driver_id
    ride.departure_time = departure

    passenger1 = MagicMock()
    passenger1.passenger_id = uuid4()
    passenger2 = MagicMock()
    passenger2.passenger_id = uuid4()

    with patch(
        "app.workers.tasks.notification_tasks.crud_ride.get_async",
        new_callable=AsyncMock,
        return_value=ride,
    ), patch(
        "app.workers.tasks.notification_tasks.crud_passenger.find_passengers_for_ride_notification",
        new_callable=AsyncMock,
        return_value=[passenger1, passenger2],
    ), patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
    ) as mock_handle_event, patch(
        "app.workers.tasks.notification_tasks.crud_scheduled_notification.create",
        new_callable=AsyncMock,
    ) as mock_sched_create:
        await handle_ride_created(db, {"ride_id": str(ride_id)})

    assert mock_handle_event.await_count == 2
    mock_sched_create.assert_awaited_once_with(
        db,
        ride_id=ride_id,
        user_id=driver_id,
        type=ScheduledNotificationType.DRIVER_REMINDER,
        deliver_at=departure - REMINDER_OFFSET,
    )


@pytest.mark.asyncio
async def test_handle_ride_created_no_departure_time_skips_scheduled_notification():
    db = AsyncMock()
    ride_id = uuid4()

    ride = MagicMock()
    ride.ride_id = ride_id
    ride.driver_id = uuid4()
    ride.departure_time = None

    with patch(
        "app.workers.tasks.notification_tasks.crud_ride.get_async",
        new_callable=AsyncMock,
        return_value=ride,
    ), patch(
        "app.workers.tasks.notification_tasks.crud_passenger.find_passengers_for_ride_notification",
        new_callable=AsyncMock,
        return_value=[],
    ), patch(
        "app.workers.tasks.notification_tasks.crud_scheduled_notification.create",
        new_callable=AsyncMock,
    ) as mock_sched_create:
        await handle_ride_created(db, {"ride_id": str(ride_id)})

    mock_sched_create.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_ride_created_passenger_notification_failure_does_not_stop_others():
    db = AsyncMock()
    ride_id = uuid4()

    ride = MagicMock()
    ride.ride_id = ride_id
    ride.driver_id = uuid4()
    ride.departure_time = None

    p1 = MagicMock(passenger_id=uuid4())
    p2 = MagicMock(passenger_id=uuid4())

    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("email service down")

    with patch(
        "app.workers.tasks.notification_tasks.crud_ride.get_async",
        new_callable=AsyncMock,
        return_value=ride,
    ), patch(
        "app.workers.tasks.notification_tasks.crud_passenger.find_passengers_for_ride_notification",
        new_callable=AsyncMock,
        return_value=[p1, p2],
    ), patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
        side_effect=side_effect,
    ) as mock_handle_event:
        await handle_ride_created(db, {"ride_id": str(ride_id)})

    assert mock_handle_event.await_count == 2


# ============================================================
# handle_booking_approved
# ============================================================


@pytest.mark.asyncio
async def test_handle_booking_approved_missing_booking_id_returns_early():
    db = AsyncMock()
    await handle_booking_approved(db, {})
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_booking_approved_booking_not_found_returns_early():
    db = AsyncMock()
    booking_id = uuid4()
    with patch(
        "app.workers.tasks.notification_tasks.crud_booking.get_booking_by_id_async",
        new_callable=AsyncMock,
        return_value=None,
    ):
        await handle_booking_approved(db, {"booking_id": str(booking_id)})


@pytest.mark.asyncio
async def test_handle_booking_approved_schedules_passenger_reminder_with_pickup_time():
    db = AsyncMock()
    booking_id = uuid4()
    passenger_id = uuid4()
    ride_id = uuid4()
    pickup_time = datetime(2026, 6, 1, 9, 30, 0)

    booking = MagicMock()
    booking.booking_id = booking_id
    booking.passenger_id = passenger_id
    booking.ride_id = ride_id
    booking.pickup_time = pickup_time
    booking.ride = MagicMock()

    with patch(
        "app.workers.tasks.notification_tasks.crud_booking.get_booking_by_id_async",
        new_callable=AsyncMock,
        return_value=booking,
    ), patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
    ), patch(
        "app.workers.tasks.notification_tasks.crud_scheduled_notification.create",
        new_callable=AsyncMock,
    ) as mock_sched_create:
        await handle_booking_approved(db, {"booking_id": str(booking_id)})

    mock_sched_create.assert_awaited_once_with(
        db,
        ride_id=ride_id,
        user_id=passenger_id,
        type=ScheduledNotificationType.PASSENGER_REMINDER,
        deliver_at=pickup_time - REMINDER_OFFSET,
    )


@pytest.mark.asyncio
async def test_handle_booking_approved_falls_back_to_ride_departure_time():
    db = AsyncMock()
    booking_id = uuid4()
    passenger_id = uuid4()
    ride_id = uuid4()
    departure = datetime(2026, 6, 1, 10, 0, 0)

    ride = MagicMock()
    ride.departure_time = departure

    booking = MagicMock()
    booking.booking_id = booking_id
    booking.passenger_id = passenger_id
    booking.ride_id = ride_id
    booking.pickup_time = None
    booking.ride = ride

    with patch(
        "app.workers.tasks.notification_tasks.crud_booking.get_booking_by_id_async",
        new_callable=AsyncMock,
        return_value=booking,
    ), patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
    ), patch(
        "app.workers.tasks.notification_tasks.crud_scheduled_notification.create",
        new_callable=AsyncMock,
    ) as mock_sched_create:
        await handle_booking_approved(db, {"booking_id": str(booking_id)})

    mock_sched_create.assert_awaited_once_with(
        db,
        ride_id=ride_id,
        user_id=passenger_id,
        type=ScheduledNotificationType.PASSENGER_REMINDER,
        deliver_at=departure - REMINDER_OFFSET,
    )


@pytest.mark.asyncio
async def test_handle_booking_approved_no_pickup_or_departure_skips_schedule():
    db = AsyncMock()
    booking_id = uuid4()

    ride = MagicMock()
    ride.departure_time = None

    booking = MagicMock()
    booking.booking_id = booking_id
    booking.passenger_id = uuid4()
    booking.ride_id = uuid4()
    booking.pickup_time = None
    booking.ride = ride

    with patch(
        "app.workers.tasks.notification_tasks.crud_booking.get_booking_by_id_async",
        new_callable=AsyncMock,
        return_value=booking,
    ), patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
    ), patch(
        "app.workers.tasks.notification_tasks.crud_scheduled_notification.create",
        new_callable=AsyncMock,
    ) as mock_sched_create:
        await handle_booking_approved(db, {"booking_id": str(booking_id)})

    mock_sched_create.assert_not_awaited()


# ============================================================
# handle_ride_cancelled_by_driver
# ============================================================


@pytest.mark.asyncio
async def test_handle_ride_cancelled_missing_ride_id_returns_early():
    db = AsyncMock()
    await handle_ride_cancelled_by_driver(db, {})
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_ride_cancelled_no_active_bookings_returns_early():
    db = AsyncMock()
    ride_id = uuid4()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
    ) as mock_handle:
        await handle_ride_cancelled_by_driver(db, {"ride_id": str(ride_id)})

    mock_handle.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_ride_cancelled_notifies_active_passengers():
    db = AsyncMock()
    ride_id = uuid4()

    confirmed_booking = MagicMock()
    confirmed_booking.status = BookingStatus.CONFIRMED.value
    confirmed_booking.passenger_id = uuid4()

    pending_booking = MagicMock()
    pending_booking.status = BookingStatus.PENDING.value
    pending_booking.passenger_id = uuid4()

    cancelled_booking = MagicMock()
    cancelled_booking.status = "cancelled"
    cancelled_booking.passenger_id = uuid4()

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [confirmed_booking, pending_booking, cancelled_booking]
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)

    with patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
    ) as mock_handle:
        await handle_ride_cancelled_by_driver(db, {"ride_id": str(ride_id)})

    assert mock_handle.await_count == 2


@pytest.mark.asyncio
async def test_handle_ride_cancelled_notification_error_continues_batch():
    db = AsyncMock()
    ride_id = uuid4()

    b1 = MagicMock(status=BookingStatus.CONFIRMED.value, passenger_id=uuid4())
    b2 = MagicMock(status=BookingStatus.CONFIRMED.value, passenger_id=uuid4())

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [b1, b2]
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)

    call_count = {"n": 0}

    async def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("push service timeout")

    with patch(
        "app.workers.tasks.notification_tasks.notification_handler.handle_event",
        new_callable=AsyncMock,
        side_effect=side_effect,
    ) as mock_handle:
        await handle_ride_cancelled_by_driver(db, {"ride_id": str(ride_id)})

    assert mock_handle.await_count == 2


# ============================================================
# handle_notification_event (RabbitMQ consumer callback)
# ============================================================


@pytest.mark.asyncio
async def test_handle_notification_event_routes_ride_cancelled():
    data = {"ride_id": str(uuid4())}
    with patch(
        "app.workers.tasks.notification_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.notification_tasks.handle_ride_cancelled_by_driver",
        new_callable=AsyncMock,
    ) as mock_handler:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await handle_notification_event(
            data, routing_key=NotificationEvent.RIDE_CANCELLED_BY_DRIVER.value
        )

    mock_handler.assert_awaited_once_with(mock_db, data)


@pytest.mark.asyncio
async def test_handle_notification_event_routes_ride_created():
    data = {"ride_id": str(uuid4())}
    with patch(
        "app.workers.tasks.notification_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.notification_tasks.handle_ride_created",
        new_callable=AsyncMock,
    ) as mock_handler:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await handle_notification_event(data, routing_key="ride.created")

    mock_handler.assert_awaited_once_with(mock_db, data)


@pytest.mark.asyncio
async def test_handle_notification_event_routes_booking_approved():
    data = {"booking_id": str(uuid4())}
    with patch(
        "app.workers.tasks.notification_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.notification_tasks.handle_booking_approved",
        new_callable=AsyncMock,
    ) as mock_handler:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await handle_notification_event(
            data, routing_key=NotificationEvent.BOOKING_APPROVED_BY_DRIVER.value
        )

    mock_handler.assert_awaited_once_with(mock_db, data)


@pytest.mark.asyncio
async def test_handle_notification_event_fallback_to_handler():
    data = {"user_id": str(uuid4())}
    mock_handler = AsyncMock()
    mock_handler.handle_event = AsyncMock()

    with patch(
        "app.workers.tasks.notification_tasks.SessionLocal",
    ) as mock_session_cls:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await handle_notification_event(
            data, routing_key="auth.email_verification", handler=mock_handler
        )

    mock_handler.handle_event.assert_awaited_once_with(
        mock_db, event_name="auth.email_verification", payload=data
    )


@pytest.mark.asyncio
async def test_handle_notification_event_exception_triggers_rollback_and_reraise():
    data = {"ride_id": str(uuid4())}

    with patch(
        "app.workers.tasks.notification_tasks.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.notification_tasks.handle_ride_created",
        new_callable=AsyncMock,
        side_effect=RuntimeError("DB dead"),
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="DB dead"):
            await handle_notification_event(data, routing_key="ride.created")

    mock_db.rollback.assert_awaited_once()


# ============================================================
# execute_reminders_job
# ============================================================


@pytest.mark.asyncio
async def test_execute_reminders_job_calls_service_run_batch():
    mock_service = AsyncMock()
    mock_service.run_batch_reminders = AsyncMock()

    with patch(
        "app.workers.tasks.notification_tasks.SessionLocal",
    ) as mock_session_cls:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await execute_reminders_job(service=mock_service)

    mock_service.run_batch_reminders.assert_awaited_once_with(mock_db)
