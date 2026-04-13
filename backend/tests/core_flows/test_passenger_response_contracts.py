"""
Response contract tests for passenger request creation.

Goal:
- Ensure `matching_rides` is always serializable as `RideResponse` objects.
- Catch regressions where service returns tuples or raw ORM shapes
  that break FastAPI response_model validation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.domain.passengers.schema import PassengerRequestCreate, PassengerRequestWithMatches
from app.domain.passengers.service import PassengerService
from app.domain.rides.enum import RideStatus
from app.domain.rides.schema import RideResponse
from tests.helpers.db_factories import make_ride, make_user


def _coords_for_name(name: str) -> tuple[float, float] | None:
    n = (name or "").lower()
    if "tel" in n:
        return (32.08, 34.78)
    if "jeru" in n:
        return (32.16, 34.99)
    return None


@pytest.mark.asyncio
async def test_passenger_request_matching_rides_is_ride_response(db_session: AsyncSession):
    driver = await make_user(db_session, "driver-contract", email_suffix="contracts")
    passenger = await make_user(db_session, "passenger-contract", email_suffix="contracts")
    ride = await make_ride(db_session, driver.user_id, status=RideStatus.OPEN)

    req_in = PassengerRequestCreate(
        num_passengers=1,
        pickup_name="Tel Aviv, Israel",
        destination_name="Jerusalem, Israel",
        search_radius=5.0,
        is_notification_active=True,
    )

    with patch(
        "app.domain.passengers.service.get_coordinates",
        new=AsyncMock(side_effect=_coords_for_name),
    ):
        created = await PassengerService.create_passenger_request(db=db_session, request_in=req_in, passenger_id=passenger.user_id)

    # Must be plain list (not SQLAlchemy result tuples)
    assert isinstance(created.matching_rides, list)
    if created.matching_rides:
        first = created.matching_rides[0]
        assert isinstance(first, RideResponse)
        ride_ids = {item.ride_id for item in created.matching_rides}
        assert ride.ride_id in ride_ids
        assert first.route_coords  # ensures route serialization field exists


@pytest.mark.asyncio
async def test_passenger_request_with_matches_model_validate_roundtrip(
    db_session: AsyncSession,
):
    """
    Explicitly validate with response schema to emulate FastAPI response_model coercion.
    """
    driver = await make_user(db_session, "driver-roundtrip", email_suffix="contracts")
    passenger = await make_user(db_session, "passenger-roundtrip", email_suffix="contracts")
    await make_ride(db_session, driver.user_id, status=RideStatus.OPEN)

    req_in = PassengerRequestCreate(
        num_passengers=1,
        pickup_name="Tel Aviv, Israel",
        destination_name="Jerusalem, Israel",
        search_radius=5.0,
        is_notification_active=True,
    )
    with patch(
        "app.domain.passengers.service.get_coordinates",
        new=AsyncMock(side_effect=_coords_for_name),
    ):
        created = await PassengerService.create_passenger_request(db=db_session, request_in=req_in, passenger_id=passenger.user_id)

    validated = PassengerRequestWithMatches.model_validate(created)
    dumped = validated.model_dump()

    assert dumped["request_id"]
    assert "matching_rides" in dumped
    assert isinstance(dumped["matching_rides"], list)
