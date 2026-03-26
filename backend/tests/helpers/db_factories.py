"""
Factories for PostgreSQL + PostGIS integration tests.

מטרות:
- למנוע שכפול קוד בין קבצי טסטים
- לייצר ישויות שמספיק "שלמות" כדי לעבור serialization של response models
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from geoalchemy2.elements import WKTElement
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401 - ensure models are registered
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride
from app.domain.users.model import User


def point_wkt(lon: float, lat: float) -> WKTElement:
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def line_wkt(points: list[tuple[float, float]]) -> WKTElement:
    """
    LINESTRING expects "lon lat" pairs.
    """
    coords = ", ".join([f"{lon} {lat}" for lon, lat in points])
    return WKTElement(f"LINESTRING({coords})", srid=4326)


async def make_user(session: AsyncSession, label: str, *, email_suffix: str = "test") -> User:
    uid = uuid4()
    u = User(
        user_id=uid,
        full_name=f"Tester {label}",
        phone_number=f"05{uid.hex[:8]}",
        email=f"{uid.hex}@{email_suffix}.linkup",
        hashed_password="not-used",
    )
    session.add(u)
    await session.flush()
    return u


async def make_ride(
    session: AsyncSession,
    driver_id,
    *,
    seats: int = 4,
    status: RideStatus = RideStatus.OPEN,
    departure_time: datetime | None = None,
    origin_lon: float = 34.78,
    origin_lat: float = 32.08,
    dest_lon: float = 34.99,
    dest_lat: float = 32.16,
) -> Ride:
    departure_time = departure_time or datetime.now(timezone.utc) + timedelta(hours=3)
    estimated = departure_time + timedelta(minutes=30)

    ride = Ride(
        ride_id=uuid4(),
        driver_id=driver_id,
        departure_time=departure_time,
        estimated_arrival_time=estimated,
        origin_name="Origin",
        destination_name="Destination",
        origin_geom=point_wkt(origin_lon, origin_lat),
        destination_geom=point_wkt(dest_lon, dest_lat),
        # Fields needed by RideResponse (otherwise ResponseValidationError)
        distance_km=1.23,
        duration_min=12.34,
        route_coords=line_wkt([(origin_lon, origin_lat), (dest_lon, dest_lat)]),
        route_summary="test-route",
        available_seats=seats,
        status=status,
    )
    session.add(ride)
    await session.flush()
    return ride


async def make_passenger_request(
    session: AsyncSession,
    passenger_id,
    *,
    when: datetime | None = None,
    pickup_name: str = "Here",
    destination_name: str = "There",
) -> PassengerRequest:
    when = when or datetime.now(timezone.utc) + timedelta(hours=2)
    pr = PassengerRequest(
        request_id=uuid4(),
        passenger_id=passenger_id,
        num_passengers=1,
        pickup_name=pickup_name,
        pickup_geom=point_wkt(34.78, 32.08),
        destination_name=destination_name,
        destination_geom=point_wkt(34.9, 32.1),
        requested_departure_time=when,
        status=PassengerStatus.ACTIVE,
        is_notification_active=True,
        is_auto_generated=False,
    )
    session.add(pr)
    await session.flush()
    return pr

