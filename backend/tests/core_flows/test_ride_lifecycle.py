"""
זרימת נהג end-to-end ב-HTTP: הזמנה מאושרת (דרך API הנוסע) → התחלת נסיעה → סיום.

משלים את test_passenger_booking_flow (נוסע + אישור) עם שלבים פעילים של נסיעה.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def _coords_for_name(name: str) -> tuple[float, float] | None:
    n = (name or "").lower()
    if "tel" in n:
        return (32.08, 34.78)
    if "jeru" in n:
        return (32.16, 34.99)
    return None


@pytest.mark.asyncio
async def test_passenger_join_approve_then_driver_starts_and_ends_ride(
    seeded_users_and_ride,
    api_client_with_overrides,
):
    client, auth_ctx = api_client_with_overrides
    driver = seeded_users_and_ride["driver"]
    passenger = seeded_users_and_ride["passenger"]
    ride = seeded_users_and_ride["ride"]

    auth_ctx["user"] = passenger
    with (
        patch(
            "app.domain.passengers.service.get_coordinates",
            new=AsyncMock(side_effect=_coords_for_name),
        ),
        patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()),
    ):
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

    with patch("app.domain.rides.service.publish_ride_event", new=AsyncMock()):
        start_res = await client.post(f"/api/v1/rides/{ride.ride_id}/start")
    assert start_res.status_code == 200, start_res.text

    with patch("app.domain.rides.service.publish_ride_event", new=AsyncMock()):
        end_res = await client.post(f"/api/v1/rides/{ride.ride_id}/end")
    assert end_res.status_code == 200, end_res.text
    assert end_res.json()["status"] == "completed"
