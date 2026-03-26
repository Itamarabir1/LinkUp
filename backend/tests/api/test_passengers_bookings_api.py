from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.db.models  # noqa: F401
from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.domain.rides.enum import RideStatus
from app.main import app
from tests.helpers.db_factories import make_ride, make_user


def _coords_for_name(name: str) -> tuple[float, float] | None:
    n = (name or "").lower()
    if "tel" in n:
        return (32.08, 34.78)
    if "jeru" in n:
        return (32.16, 34.99)
    return None


@pytest_asyncio.fixture
async def seeded_users_and_ride(e2e_session_factory: async_sessionmaker):
    async with e2e_session_factory() as s:
        driver = await make_user(s, "api-driver", email_suffix="api")
        passenger = await make_user(s, "api-passenger", email_suffix="api")
        ride = await make_ride(s, driver.user_id, status=RideStatus.OPEN, seats=2)
        await s.commit()
        return {
            "driver": driver,
            "passenger": passenger,
            "ride": ride,
        }


@pytest_asyncio.fixture
async def api_client_with_overrides(
    e2e_session_factory: async_sessionmaker,
) -> AsyncGenerator[tuple[AsyncClient, dict], None]:
    auth_ctx: dict[str, object] = {"user": None}

    async def _get_db_override():
        async with e2e_session_factory() as s:
            yield s

    async def _get_current_user_override():
        user = auth_ctx.get("user")
        if user is None:
            raise RuntimeError("Test auth context missing user")
        return user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        try:
            yield client, auth_ctx
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_request_ride_from_search_then_approve_flow(
    seeded_users_and_ride,
    api_client_with_overrides,
):
    """
    Long flow at HTTP layer:
    - passenger sends /request-ride-from-search (which may create request + join)
    - driver approves booking
    """
    client, auth_ctx = api_client_with_overrides
    driver = seeded_users_and_ride["driver"]
    passenger = seeded_users_and_ride["passenger"]
    ride = seeded_users_and_ride["ride"]

    auth_ctx["user"] = passenger
    with patch(
        "app.domain.passengers.service.get_coordinates",
        new=AsyncMock(side_effect=_coords_for_name),
    ), patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()):
        join_res = await client.post(
            "/api/v1/passenger/passengers/request-ride-from-search",
            json={
                "ride_id": str(ride.ride_id),
                "pickup_name": "Tel Aviv, Israel",
                "destination_name": "Jerusalem, Israel",
                "num_seats": 1,
            },
        )
    assert join_res.status_code == 201, join_res.text
    booking_id = join_res.json()["booking_id"]

    auth_ctx["user"] = driver
    with patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()):
        approve_res = await client.patch(
            f"/api/v1/bookings/{booking_id}/approve",
            params={"driver_id": str(driver.user_id)},
        )
    assert approve_res.status_code == 200, approve_res.text
    assert approve_res.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_request_then_join_cross_request_regression_guard(
    seeded_users_and_ride,
    api_client_with_overrides,
):
    """
    Regression guard for the real k6 pattern:
    POST /passenger/passengers  -> then POST /bookings/request-to-join.
    If transaction handling regresses, join may return BOOKING_REQUEST_NOT_FOUND.
    """
    client, auth_ctx = api_client_with_overrides
    passenger = seeded_users_and_ride["passenger"]
    ride = seeded_users_and_ride["ride"]
    auth_ctx["user"] = passenger

    with patch(
        "app.domain.passengers.service.get_coordinates",
        new=AsyncMock(side_effect=_coords_for_name),
    ), patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()):
        req_res = await client.post(
            "/api/v1/passenger/passengers/",
            json={
                "num_passengers": 1,
                "pickup_name": "Tel Aviv, Israel",
                "destination_name": "Jerusalem, Israel",
                "requested_departure_time": "2032-01-01T10:00:00Z",
                "search_radius": 5000,
                "is_notification_active": True,
                "pickup_lat": 32.0853,
                "pickup_lon": 34.7818,
            },
        )
    assert req_res.status_code == 201, req_res.text
    request_id = req_res.json()["request_id"]

    with patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()):
        join_res = await client.post(
            "/api/v1/bookings/request-to-join",
            json={"ride_id": str(ride.ride_id), "request_id": request_id, "num_seats": 1},
        )

    assert join_res.status_code == 201, join_res.text

