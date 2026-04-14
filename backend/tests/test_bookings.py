"""
Integration tests for BookingService.

Requires DATABASE_URL (PostgreSQL + asyncpg + PostGIS); see tests/conftest.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401 — register models on Base
from app.core.exceptions.booking import BookingAlreadyExistsError
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.service import BookingService

from tests.helpers.db_factories import make_passenger_request, make_ride, make_user


@pytest.mark.asyncio
async def test_request_to_join_creates_pending_booking(db_session: AsyncSession):
    """request_to_join creates pending booking and publishes outbox."""
    driver = await make_user(db_session, "driver", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        booking = await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    assert booking.status == BookingStatus.PENDING
    assert booking.ride_id == ride.ride_id
    assert booking.passenger_id == passenger.user_id
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_booking_raises_error(db_session: AsyncSession):
    """Same passenger cannot book the same ride twice."""
    driver = await make_user(db_session, "driver2", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger2", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id)
    req1 = await make_passenger_request(db_session, passenger.user_id)
    req2 = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ):
        await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            req1.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

        with pytest.raises(BookingAlreadyExistsError):
            await BookingService.request_to_join(
                db_session,
                ride.ride_id,
                req2.request_id,
                num_seats=1,
                current_user_id=passenger.user_id,
            )


@pytest.mark.asyncio
async def test_approve_booking_changes_status(db_session: AsyncSession):
    """approve_booking moves status to confirmed and publishes outbox."""
    driver = await make_user(db_session, "driver3", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger3", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ):
        booking = await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        approved = await BookingService.approve_booking(
            db_session,
            booking.booking_id,
            driver.user_id,
        )

    assert approved.status == BookingStatus.CONFIRMED
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_reject_booking_changes_status_and_outbox(db_session: AsyncSession):
    """reject_booking sets rejected and publishes outbox."""
    driver = await make_user(db_session, "driver4", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger4", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ):
        booking = await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        rejected = await BookingService.reject_booking(
            db_session,
            booking.booking_id,
            driver.user_id,
        )

    assert rejected.status == BookingStatus.REJECTED
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_get_driver_summary_embeds_passengers(db_session: AsyncSession):
    """Driver summary returns rides with pending/confirmed passengers in one service call."""
    driver = await make_user(db_session, "drv_sum", email_suffix="bookings")
    passenger = await make_user(db_session, "pax_sum", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    summary = await BookingService.get_driver_summary(db_session, driver.user_id)
    assert len(summary.rides) >= 1
    match = next((r for r in summary.rides if str(r.ride_id) == str(ride.ride_id)), None)
    assert match is not None
    assert len(match.passengers) == 1
    assert match.passengers[0].passenger_name


@pytest.mark.asyncio
async def test_get_passenger_summary_includes_driver_when_ride_open(db_session: AsyncSession):
    """Passenger summary embeds driver for non-terminal ride statuses."""
    driver = await make_user(db_session, "drv_ps", email_suffix="bookings")
    passenger = await make_user(db_session, "pax_ps", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    summary = await BookingService.get_passenger_summary(db_session, passenger.user_id)
    assert len(summary.bookings) >= 1
    row = summary.bookings[0]
    assert row.driver is not None
    assert row.driver.full_name
