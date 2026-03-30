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

    with (
        patch(
            "app.domain.passengers.service.get_coordinates",
            new=AsyncMock(side_effect=_coords_for_name),
        ),
        patch("app.domain.bookings.service.publish_to_outbox", new=AsyncMock()),
    ):
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
