from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.core.exceptions.booking import ForbiddenRideActionError
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
    u = User(
        user_id=uid,
        full_name=f"Tester {label}",
        phone_number=f"05{uid.hex[:8]}",
        email=f"{uid.hex}@permissions.test",
        hashed_password="not-used",
    )
    session.add(u)
    await session.flush()
    return u


async def _make_ride(session: AsyncSession, driver_id) -> Ride:
    ride = Ride(
        ride_id=uuid4(),
        driver_id=driver_id,
        departure_time=datetime.now(timezone.utc),
        origin_name="A",
        destination_name="B",
        origin_geom=_point(34.78, 32.08),
        destination_geom=_point(34.99, 32.16),
        available_seats=4,
        status=RideStatus.OPEN,
    )
    session.add(ride)
    await session.flush()
    return ride


async def _make_passenger_request(session: AsyncSession, passenger_id) -> PassengerRequest:
    req = PassengerRequest(
        request_id=uuid4(),
        passenger_id=passenger_id,
        num_passengers=1,
        pickup_name="Here",
        pickup_geom=_point(34.78, 32.08),
        destination_name="There",
        destination_geom=_point(34.9, 32.1),
        requested_departure_time=datetime.now(timezone.utc),
        status=PassengerStatus.ACTIVE,
    )
    session.add(req)
    await session.flush()
    return req


@pytest.mark.asyncio
async def test_request_to_join_rejects_non_owner_request(db_session: AsyncSession):
    """משתמש לא יכול להצטרף עם request_id שלא שייך לו."""
    driver = await _make_user(db_session, "driver")
    passenger = await _make_user(db_session, "passenger")
    attacker = await _make_user(db_session, "attacker")
    ride = await _make_ride(db_session, driver.user_id)
    passenger_request = await _make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        with pytest.raises(ForbiddenRideActionError):
            await BookingService.request_to_join(
                db_session,
                ride.ride_id,
                passenger_request.request_id,
                num_seats=1,
                current_user_id=attacker.user_id,
            )

    mock_publish.assert_not_awaited()
