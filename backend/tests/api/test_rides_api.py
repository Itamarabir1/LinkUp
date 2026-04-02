from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.db.models  # noqa: F401
from app.domain.bookings.enum import BookingStatus
from app.domain.rides.enum import RideStatus
from tests.helpers.db_factories import make_booking, make_ride, make_user


@pytest_asyncio.fixture
async def seeded_ride_confirmed_booking(e2e_session_factory: async_sessionmaker):
    async with e2e_session_factory() as s:
        driver = await make_user(s, "http-rd", email_suffix="ridesapi")
        passenger = await make_user(s, "http-rp", email_suffix="ridesapi")
        ride = await make_ride(s, driver.user_id, status=RideStatus.OPEN, seats=4)
        await make_booking(s, ride.ride_id, passenger.user_id, status=BookingStatus.CONFIRMED)
        await s.commit()
        return {"driver": driver, "passenger": passenger, "ride": ride}


@pytest.mark.asyncio
async def test_get_ride_by_id_returns_200(seeded_ride_confirmed_booking, api_client_with_overrides):
    client, _ = api_client_with_overrides
    ride = seeded_ride_confirmed_booking["ride"]
    res = await client.get(f"/api/v1/rides/{ride.ride_id}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ride_id"] == str(ride.ride_id)


@pytest.mark.asyncio
async def test_driver_patch_seats(
    seeded_ride_confirmed_booking,
    api_client_with_overrides,
):
    client, auth_ctx = api_client_with_overrides
    driver = seeded_ride_confirmed_booking["driver"]
    ride = seeded_ride_confirmed_booking["ride"]
    auth_ctx["user"] = driver
    with (
        patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock),
        patch("app.domain.rides.service.broadcast.publish", new_callable=AsyncMock),
    ):
        res = await client.patch(
            f"/api/v1/rides/{ride.ride_id}",
            json={"available_seats": 3},
        )
    assert res.status_code == 200, res.text
    assert res.json()["available_seats"] == 3


@pytest.mark.asyncio
async def test_start_then_end_ride_http(
    seeded_ride_confirmed_booking,
    api_client_with_overrides,
):
    client, auth_ctx = api_client_with_overrides
    driver = seeded_ride_confirmed_booking["driver"]
    ride = seeded_ride_confirmed_booking["ride"]
    auth_ctx["user"] = driver

    with patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock):
        start_res = await client.post(f"/api/v1/rides/{ride.ride_id}/start")
    assert start_res.status_code == 200, start_res.text
    assert start_res.json()["status"] == "active"

    with patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock):
        end_res = await client.post(f"/api/v1/rides/{ride.ride_id}/end")
    assert end_res.status_code == 200, end_res.text
    assert end_res.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_cancel_ride_http_204(
    seeded_ride_confirmed_booking,
    api_client_with_overrides,
):
    client, auth_ctx = api_client_with_overrides
    driver = seeded_ride_confirmed_booking["driver"]
    ride = seeded_ride_confirmed_booking["ride"]
    auth_ctx["user"] = driver
    with (
        patch("app.domain.rides.service.publish_to_outbox", new_callable=AsyncMock),
        patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock),
        patch("app.domain.rides.service.broadcast.publish", new_callable=AsyncMock),
    ):
        res = await client.delete(f"/api/v1/rides/{ride.ride_id}/cancel")
    assert res.status_code == 204, res.text
