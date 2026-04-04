"""
בדיקות הרשאות לנתיבי bookings ו-passengers שתוקנו ב-P0.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.bookings.enum import BookingStatus
from app.domain.rides.enum import RideStatus
from tests.helpers.db_factories import (
    make_booking,
    make_passenger_request,
    make_ride,
    make_user,
)


@pytest_asyncio.fixture
async def seeded_booking(e2e_session_factory: async_sessionmaker):
    async with e2e_session_factory() as s:
        driver = await make_user(s, "perm-d", email_suffix="perms")
        passenger = await make_user(s, "perm-p", email_suffix="perms")
        other = await make_user(s, "perm-o", email_suffix="perms")
        ride = await make_ride(s, driver.user_id, status=RideStatus.OPEN, seats=4)
        booking = await make_booking(
            s,
            ride.ride_id,
            passenger.user_id,
            status=BookingStatus.PENDING,
        )
        await s.commit()
        return {
            "driver": driver,
            "passenger": passenger,
            "other": other,
            "ride": ride,
            "booking": booking,
        }


@pytest_asyncio.fixture
async def seeded_passenger_request(seeded_booking, e2e_session_factory):
    async with e2e_session_factory() as s:
        pr = await make_passenger_request(
            s,
            seeded_booking["passenger"].user_id,
        )
        await s.commit()
        return pr


# --- approve ---


@pytest.mark.asyncio
async def test_approve_no_auth_returns_401(seeded_booking, api_client_no_auth):
    booking_id = seeded_booking["booking"].booking_id
    res = await api_client_no_auth.patch(f"/api/v1/bookings/{booking_id}/approve")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_approve_wrong_driver_returns_403(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["other"]
    booking_id = seeded_booking["booking"].booking_id
    res = await client.patch(f"/api/v1/bookings/{booking_id}/approve")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_approve_correct_driver_succeeds(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["driver"]
    booking_id = seeded_booking["booking"].booking_id
    with patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()):
        res = await client.patch(f"/api/v1/bookings/{booking_id}/approve")
    assert res.status_code == 200
    assert res.json()["status"] == "confirmed"


# --- reject ---


@pytest.mark.asyncio
async def test_reject_no_auth_returns_401(seeded_booking, api_client_no_auth):
    booking_id = seeded_booking["booking"].booking_id
    res = await api_client_no_auth.patch(f"/api/v1/bookings/{booking_id}/reject")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_reject_wrong_driver_returns_403(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["other"]
    booking_id = seeded_booking["booking"].booking_id
    res = await client.patch(f"/api/v1/bookings/{booking_id}/reject")
    assert res.status_code == 403


# --- get_booking ---


@pytest.mark.asyncio
async def test_get_booking_third_party_returns_403(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["other"]
    booking_id = seeded_booking["booking"].booking_id
    res = await client.get(f"/api/v1/bookings/{booking_id}")
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_get_booking_passenger_succeeds(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["passenger"]
    booking_id = seeded_booking["booking"].booking_id
    res = await client.get(f"/api/v1/bookings/{booking_id}")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_get_booking_driver_succeeds(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["driver"]
    booking_id = seeded_booking["booking"].booking_id
    res = await client.get(f"/api/v1/bookings/{booking_id}")
    assert res.status_code == 200


# --- /all admin endpoint ---


@pytest.mark.asyncio
async def test_get_all_rides_non_admin_returns_403(seeded_booking, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    passenger = seeded_booking["passenger"]
    passenger.is_admin = False
    auth_ctx["user"] = passenger
    res = await client.get("/api/v1/passenger/passengers/all")
    assert res.status_code == 403


# --- /matches ownership ---


@pytest.mark.asyncio
async def test_get_matches_wrong_owner_returns_403(
    seeded_booking, seeded_passenger_request, api_client_with_overrides
):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["other"]
    res = await client.get(
        f"/api/v1/passenger/passengers/{seeded_passenger_request.request_id}/matches"
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_get_matches_correct_owner_succeeds(
    seeded_booking, seeded_passenger_request, api_client_with_overrides
):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_booking["passenger"]
    res = await client.get(
        f"/api/v1/passenger/passengers/{seeded_passenger_request.request_id}/matches"
    )
    assert res.status_code == 200
