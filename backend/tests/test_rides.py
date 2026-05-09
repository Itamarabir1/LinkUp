"""
אינטגרציה ל-RideService מול PostgreSQL.

Redis / שידורים — ממוקים; Outbox בביטול נסיעה — ממוקה.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.core.exceptions.base import LinkUpError
from app.core.exceptions.ride import InvalidRideStatusError, NoConfirmedBookingsError, RideNotFoundError
from app.domain.notifications.constants import NotificationEvent
from app.domain.rides.enum import RideStatus
from app.domain.rides.schema import RideUpdate
from app.domain.rides.service import RideService

from tests.helpers.db_factories import make_booking, make_ride, make_user


@pytest.mark.asyncio
async def test_get_my_rides_returns_only_for_driver(db_session: AsyncSession):
    driver_a = await make_user(db_session, "rA", email_suffix="rides")
    driver_b = await make_user(db_session, "rB", email_suffix="rides")
    await make_ride(db_session, driver_a.user_id)
    await make_ride(db_session, driver_b.user_id)

    svc = RideService()
    mine = await svc.get_my_rides(db_session, driver_a.user_id, status=None)
    assert len(mine.rides) == 1
    assert str(mine.rides[0].driver_id) == str(driver_a.user_id)


@pytest.mark.asyncio
async def test_get_my_rides_filters_by_status(db_session: AsyncSession):
    driver = await make_user(db_session, "rStat", email_suffix="rides")
    await make_ride(db_session, driver.user_id, status=RideStatus.OPEN)
    await make_ride(db_session, driver.user_id, status=RideStatus.COMPLETED)

    svc = RideService()
    open_only = await svc.get_my_rides(db_session, driver.user_id, status="open")
    assert len(open_only.rides) == 1
    assert open_only.rides[0].status == RideStatus.OPEN


@pytest.mark.asyncio
async def test_update_ride_empty_payload_raises(db_session: AsyncSession):
    driver = await make_user(db_session, "rUpd0", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id)
    svc = RideService()
    with pytest.raises(LinkUpError) as exc:
        await svc.update_ride(db_session, ride.ride_id, driver.user_id, RideUpdate())
    assert exc.value.error_code == "RIDE_UPDATE_EMPTY_FIELDS"


@pytest.mark.asyncio
async def test_update_ride_seats_and_broadcast_mocked(db_session: AsyncSession):
    driver = await make_user(db_session, "rUpd1", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    svc = RideService()
    new_dep = ride.departure_time + timedelta(hours=1)
    with (
        patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock) as mock_pub,
        patch("app.domain.rides.service.broadcast.publish", new_callable=AsyncMock) as mock_bc,
    ):
        out = await svc.update_ride(
            db_session,
            ride.ride_id,
            driver.user_id,
            RideUpdate(departure_time=new_dep, available_seats=3),
        )
    assert out.available_seats == 3
    mock_pub.assert_called_once()
    mock_bc.assert_called_once()


@pytest.mark.asyncio
async def test_start_ride_without_confirmed_raises(db_session: AsyncSession):
    driver = await make_user(db_session, "rSt0", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id)
    svc = RideService()
    with pytest.raises(NoConfirmedBookingsError):
        await svc.start_ride(db_session, ride.ride_id, driver.user_id)


@pytest.mark.asyncio
async def test_start_then_end_ride_lifecycle(db_session: AsyncSession):
    driver = await make_user(db_session, "rLife", email_suffix="rides")
    passenger = await make_user(db_session, "rPas", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    await make_booking(db_session, ride.ride_id, passenger.user_id)

    svc = RideService()
    with patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock):
        started = await svc.start_ride(db_session, ride.ride_id, driver.user_id)
    assert started.status == RideStatus.ACTIVE

    with patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock):
        ended = await svc.end_ride(db_session, ride.ride_id, driver.user_id)
    assert ended.status == RideStatus.COMPLETED


@pytest.mark.asyncio
async def test_end_ride_while_open_raises(db_session: AsyncSession):
    driver = await make_user(db_session, "rEndBad", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id)
    svc = RideService()
    with pytest.raises(InvalidRideStatusError):
        await svc.end_ride(db_session, ride.ride_id, driver.user_id)


@pytest.mark.asyncio
async def test_cancel_ride_by_driver_outbox_and_broadcast_mocked(db_session: AsyncSession):
    driver = await make_user(db_session, "rCan", email_suffix="rides")
    passenger = await make_user(db_session, "rCanP", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id)
    await make_booking(db_session, ride.ride_id, passenger.user_id)

    svc = RideService()
    with (
        patch("app.domain.rides.service.publish_to_outbox", new_callable=AsyncMock) as mock_ob,
        patch("app.domain.rides.service.publish_ride_event", new_callable=AsyncMock),
        patch("app.domain.rides.service.broadcast.publish", new_callable=AsyncMock),
    ):
        await svc.cancel_ride_by_driver(db_session, ride.ride_id, driver.user_id)

    mock_ob.assert_called_once()
    call_kw = mock_ob.call_args
    assert call_kw[0][1] == NotificationEvent.RIDE_CANCELLED_BY_DRIVER.value

    refreshed = await svc.get_ride_by_id(db_session, ride.ride_id)
    assert refreshed is not None
    assert refreshed.status == RideStatus.CANCELLED


@pytest.mark.asyncio
async def test_update_ride_wrong_driver_returns_not_found(db_session: AsyncSession):
    driver = await make_user(db_session, "rOwn", email_suffix="rides")
    other = await make_user(db_session, "rOth", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id)
    svc = RideService()
    with pytest.raises(RideNotFoundError):
        await svc.update_ride(
            db_session,
            ride.ride_id,
            other.user_id,
            RideUpdate(available_seats=2),
        )


@pytest.mark.asyncio
async def test_get_ride_by_id_missing_returns_none(db_session: AsyncSession):
    svc = RideService()
    assert await svc.get_ride_by_id(db_session, uuid4()) is None


@pytest.mark.asyncio
async def test_get_ride_by_id_found(db_session: AsyncSession):
    driver = await make_user(db_session, "rGet", email_suffix="rides")
    ride = await make_ride(db_session, driver.user_id)
    svc = RideService()
    got = await svc.get_ride_by_id(db_session, ride.ride_id)
    assert got is not None
    assert got.ride_id == ride.ride_id
