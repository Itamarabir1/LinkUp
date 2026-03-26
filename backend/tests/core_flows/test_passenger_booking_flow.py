"""
Core flow tests (service-level) that mirror the k6 pipeline:

- create PassengerRequest (with matching rides computed)
  - catches ResponseValidationError-style bugs where matching_rides isn't serializable
- join ride (request-to-join)
- approve booking
- reject another booking
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.service import BookingService
from app.domain.passengers.schema import PassengerRequestCreate
from app.domain.passengers.service import PassengerService
from app.domain.rides.enum import RideStatus
from app.domain.rides.schema import RideResponse
from tests.helpers.db_factories import make_ride, make_user


def _coords_for_name(name: str) -> tuple[float, float] | None:
    """
    Return coords that match our test ride line.
    We use "Tel Aviv" / "Jerusalem" strings to mimic load test inputs.
    """
    n = (name or "").lower()
    if "tel" in n:
        return (32.08, 34.78)
    if "jeru" in n:
        return (32.16, 34.99)
    return None


@pytest.mark.asyncio
async def test_flow_create_request_join_approve_reject(db_session: AsyncSession):
    driver = await make_user(db_session, "driver-flow", email_suffix="flow")
    passenger1 = await make_user(db_session, "p1-flow", email_suffix="flow")
    passenger2 = await make_user(db_session, "p2-flow", email_suffix="flow")

    ride = await make_ride(db_session, driver.user_id, status=RideStatus.OPEN, seats=2)

    # Patch external calls used by passenger request creation.
    with patch(
        "app.domain.passengers.service.get_coordinates",
        new=AsyncMock(side_effect=_coords_for_name),
    ):
        req_in = PassengerRequestCreate(
            num_passengers=1,
            pickup_name="Tel Aviv, Israel",
            destination_name="Jerusalem, Israel",
            search_radius=5000,
            is_notification_active=True,
        )
        created = await PassengerService.create_passenger_request(
            db=db_session, request_in=req_in, passenger_id=passenger1.user_id
        )

    # Contract-level assertions: ensure matching_rides is a list of serializable RideResponse.
    assert hasattr(created, "matching_rides")
    assert isinstance(created.matching_rides, list)
    if created.matching_rides:
        assert isinstance(created.matching_rides[0], RideResponse)
        ride_ids = {item.ride_id for item in created.matching_rides}
        assert ride.ride_id in ride_ids

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        booking1 = await BookingService.request_to_join(
            db_session,
            ride_id=ride.ride_id,
            request_id=created.request_id,
            num_seats=1,
            current_user_id=passenger1.user_id,
        )

    assert booking1.status == BookingStatus.PENDING

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        approved = await BookingService.approve_booking(
            db_session, booking_id=booking1.booking_id, driver_id=driver.user_id
        )

    assert approved.status == BookingStatus.CONFIRMED

    # Second passenger requests then gets rejected.
    with patch(
        "app.domain.passengers.service.get_coordinates",
        new=AsyncMock(side_effect=_coords_for_name),
    ):
        req2_in = PassengerRequestCreate(
            num_passengers=1,
            pickup_name="Tel Aviv, Israel",
            destination_name="Jerusalem, Israel",
            search_radius=5000,
            is_notification_active=True,
        )
        created2 = await PassengerService.create_passenger_request(
            db=db_session, request_in=req2_in, passenger_id=passenger2.user_id
        )

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        booking2 = await BookingService.request_to_join(
            db_session,
            ride_id=ride.ride_id,
            request_id=created2.request_id,
            num_seats=1,
            current_user_id=passenger2.user_id,
        )

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        rejected = await BookingService.reject_booking(
            db_session, booking_id=booking2.booking_id, driver_id=driver.user_id
        )

    assert rejected.status == BookingStatus.REJECTED

