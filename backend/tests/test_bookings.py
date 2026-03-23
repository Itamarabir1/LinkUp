"""
טסטי אינטגרציה ל-BookingService.

דורשים TEST_DATABASE_URL (PostgreSQL + asyncpg + PostGIS) — ראו tests/conftest.py.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401 — רישום מודלים ב-Base
from app.core.exceptions.booking import BookingAlreadyExistsError
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.service import BookingService
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride
from app.domain.users.model import User


def _point(lon: float, lat: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


async def _make_user(session: AsyncSession, label: str) -> User:
    uid = uuid4()
    phone = f"05{uid.hex[:8]}"
    u = User(
        user_id=uid,
        full_name=f"Tester {label}",
        phone_number=phone,
        email=f"{uid.hex}@bookings.test",
        hashed_password="not-used",
    )
    session.add(u)
    await session.flush()
    return u


async def _make_ride(session: AsyncSession, driver_id, seats: int = 4) -> Ride:
    r = Ride(
        ride_id=uuid4(),
        driver_id=driver_id,
        departure_time=datetime.now(timezone.utc),
        origin_name="A",
        destination_name="B",
        origin_geom=_point(34.78, 32.08),
        destination_geom=_point(34.99, 32.16),
        available_seats=seats,
        status=RideStatus.OPEN,
    )
    session.add(r)
    await session.flush()
    return r


async def _make_passenger_request(
    session: AsyncSession, passenger_id, when: datetime | None = None
) -> PassengerRequest:
    when = when or datetime.now(timezone.utc)
    pr = PassengerRequest(
        request_id=uuid4(),
        passenger_id=passenger_id,
        num_passengers=1,
        pickup_name="Here",
        pickup_geom=_point(34.78, 32.08),
        destination_name="There",
        destination_geom=_point(34.9, 32.1),
        requested_departure_time=when,
        status=PassengerStatus.ACTIVE,
    )
    session.add(pr)
    await session.flush()
    return pr


@pytest.mark.asyncio
async def test_request_to_join_creates_pending_booking(db_session: AsyncSession):
    """זרימת הזמנה — נוצר booking עם status pending_approval ונקרא outbox."""
    driver = await _make_user(db_session, "driver")
    passenger = await _make_user(db_session, "passenger")
    ride = await _make_ride(db_session, driver.user_id)
    p_req = await _make_passenger_request(db_session, passenger.user_id)

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
    """אותו נוסע לא יכול להזמין פעמיים לאותה נסיעה (בקשה שנייה)."""
    driver = await _make_user(db_session, "driver2")
    passenger = await _make_user(db_session, "passenger2")
    ride = await _make_ride(db_session, driver.user_id)
    req1 = await _make_passenger_request(db_session, passenger.user_id)
    req2 = await _make_passenger_request(db_session, passenger.user_id)

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
    """אישור הזמנה — status הופך ל-confirmed ונקרא outbox."""
    driver = await _make_user(db_session, "driver3")
    passenger = await _make_user(db_session, "passenger3")
    ride = await _make_ride(db_session, driver.user_id, seats=4)
    p_req = await _make_passenger_request(db_session, passenger.user_id)

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
