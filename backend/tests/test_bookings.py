"""
Integration tests for BookingService.

Requires DATABASE_URL (PostgreSQL + asyncpg + PostGIS); see tests/conftest.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401 — register models on Base
from app.core.exceptions.booking import BookingAlreadyExistsError
from app.core.exceptions.validation import BadRequestError
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.booking_reads_service import BookingReadsService
from app.domain.bookings.service import BookingService
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.service import PassengerService
from app.domain.rides.enum import RideStatus

from tests.helpers.db_factories import make_booking, make_passenger_request, make_ride, make_user


@pytest.mark.asyncio
async def test_request_to_join_creates_pending_booking(db_session: AsyncSession):
    """request_to_join creates pending booking and publishes outbox."""
    driver = await make_user(db_session, "driver", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        booking = await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    assert booking.status == BookingStatus.PENDING
    assert booking.ride_id == ride.ride_id
    assert booking.passenger_id == passenger.user_id
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_duplicate_booking_raises_error(db_session: AsyncSession):
    """Same passenger cannot book the same ride twice."""
    driver = await make_user(db_session, "driver2", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger2", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id)
    req1 = await make_passenger_request(db_session, passenger.user_id)
    req2 = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ):
        await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            req1.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

        with pytest.raises(BookingAlreadyExistsError):
            await BookingService.request_to_join(
                db_session,
                ride.ride_id,
                req2.request_id,
                num_seats=1,
                current_user_id=passenger.user_id,
            )


@pytest.mark.asyncio
async def test_approve_booking_changes_status(db_session: AsyncSession):
    """approve_booking moves status to confirmed and publishes outbox."""
    driver = await make_user(db_session, "driver3", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger3", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ):
        booking = await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        approved = await BookingService.approve_booking(
            db_session,
            booking.booking_id,
            driver.user_id,
        )

    assert approved.status == BookingStatus.CONFIRMED
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_reject_booking_changes_status_and_outbox(db_session: AsyncSession):
    """reject_booking sets rejected and publishes outbox."""
    driver = await make_user(db_session, "driver4", email_suffix="bookings")
    passenger = await make_user(db_session, "passenger4", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ):
        booking = await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        rejected = await BookingService.reject_booking(
            db_session,
            booking.booking_id,
            driver.user_id,
        )

    assert rejected.status == BookingStatus.REJECTED
    mock_publish.assert_called_once()


@pytest.mark.asyncio
async def test_get_driver_active_summary_embeds_passengers(db_session: AsyncSession):
    """Driver active summary returns active rides with passengers embedded in one service call."""
    driver = await make_user(db_session, "drv_sum", email_suffix="bookings")
    passenger = await make_user(db_session, "pax_sum", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    summary = await BookingReadsService.get_driver_active_summary(db_session, driver.user_id)
    assert len(summary.rides) >= 1
    match = next((r for r in summary.rides if str(r.ride_id) == str(ride.ride_id)), None)
    assert match is not None
    assert len(match.passengers) == 1
    assert match.passengers[0].passenger_name


@pytest.mark.asyncio
async def test_get_passenger_active_summary_includes_driver_when_ride_open(db_session: AsyncSession):
    """Passenger active summary embeds driver for non-terminal ride statuses."""
    driver = await make_user(db_session, "drv_ps", email_suffix="bookings")
    passenger = await make_user(db_session, "pax_ps", email_suffix="bookings")
    ride = await make_ride(db_session, driver.user_id, seats=4)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    with patch("app.domain.bookings.service.publish_to_outbox", new_callable=AsyncMock):
        await BookingService.request_to_join(
            db_session,
            ride.ride_id,
            p_req.request_id,
            num_seats=1,
            current_user_id=passenger.user_id,
        )

    summary = await BookingReadsService.get_passenger_active_summary(db_session, passenger.user_id)
    assert len(summary.bookings) >= 1
    row = summary.bookings[0]
    assert row.driver is not None
    assert row.driver.full_name


@pytest.mark.asyncio
async def test_notifications_cursor_pagination_first_page_and_next_cursor(db_session: AsyncSession):
    """Notifications feed returns keyset-paginated items ordered by created_at/booking_id desc."""
    passenger = await make_user(db_session, "notif_pax", email_suffix="bookings")
    p_req = await make_passenger_request(db_session, passenger.user_id)

    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(6):
        driver = await make_user(db_session, f"notif_drv_{i}", email_suffix="bookings")
        ride = await make_ride(db_session, driver.user_id, seats=4)
        status = BookingStatus.PENDING if i % 2 == 0 else BookingStatus.CONFIRMED
        b = await make_booking(
            db_session,
            ride.ride_id,
            passenger.user_id,
            status=status,
            request_id=p_req.request_id,
            num_seats=1,
        )
        b.created_at = base + timedelta(seconds=i)
    await db_session.flush()

    page1 = await BookingReadsService.get_notifications_for_user(
        db_session,
        passenger.user_id,
        limit=3,
    )
    assert len(page1.items) == 3
    assert page1.has_more is True
    assert page1.next_cursor is not None
    assert page1.limit == 3
    assert all(
        page1.items[i].created_at >= page1.items[i + 1].created_at
        for i in range(len(page1.items) - 1)
    )

    page2 = await BookingReadsService.get_notifications_for_user(
        db_session,
        passenger.user_id,
        limit=3,
        after=page1.next_cursor,
    )
    assert len(page2.items) >= 1
    ids1 = {str(i.booking_id) for i in page1.items}
    ids2 = {str(i.booking_id) for i in page2.items}
    assert ids1.isdisjoint(ids2)


@pytest.mark.asyncio
async def test_notifications_invalid_cursor_raises_bad_request(db_session: AsyncSession):
    """Invalid notifications cursor should raise user-facing bad request."""
    user = await make_user(db_session, "notif_bad_cursor", email_suffix="bookings")
    with pytest.raises(BadRequestError) as exc_info:
        await BookingReadsService.get_notifications_for_user(
            db_session,
            user.user_id,
            limit=5,
            after="not-a-cursor",
        )
    assert "מסמן עמוד לא תקין" in str(exc_info.value)


# ---------------------------------------------------------------------------
# PassengerService.cancel_request — bulk path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_request_with_no_bookings_only_updates_status(db_session: AsyncSession):
    """N=0: only PassengerRequest.status flips to CANCELLED."""
    passenger = await make_user(db_session, "cr_none", email_suffix="cancel")
    p_req = await make_passenger_request(db_session, passenger.user_id)

    result = await PassengerService.cancel_request(db_session, p_req.request_id, passenger.user_id)

    await db_session.refresh(p_req)
    assert result["message"]
    assert p_req.status == PassengerStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_request_pending_only_no_seat_changes(db_session: AsyncSession):
    """N=3 PENDING bookings on one ride — no seat math, ride untouched."""
    driver = await make_user(db_session, "cr_drv1", email_suffix="cancel")
    passenger = await make_user(db_session, "cr_pax1", email_suffix="cancel")
    ride = await make_ride(db_session, driver.user_id, seats=4, status=RideStatus.OPEN)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    bookings = [
        await make_booking(
            db_session,
            ride.ride_id,
            passenger.user_id,
            status=BookingStatus.PENDING,
            num_seats=1,
            request_id=p_req.request_id,
        )
    ]
    # Two more PENDING bookings against the same ride from other passengers
    for label in ("p2", "p3"):
        other = await make_user(db_session, f"cr_{label}", email_suffix="cancel")
        bookings.append(
            await make_booking(
                db_session,
                ride.ride_id,
                other.user_id,
                status=BookingStatus.PENDING,
                num_seats=1,
                request_id=p_req.request_id,
            ),
        )

    await PassengerService.cancel_request(db_session, p_req.request_id, passenger.user_id)

    await db_session.refresh(ride)
    await db_session.refresh(p_req)
    for b in bookings:
        await db_session.refresh(b)

    assert ride.available_seats == 4
    assert ride.status == RideStatus.OPEN
    assert p_req.status == PassengerStatus.CANCELLED
    assert all(b.status == BookingStatus.CANCELLED for b in bookings)


@pytest.mark.asyncio
async def test_cancel_request_confirmed_same_ride_restores_seats(db_session: AsyncSession):
    """Two CONFIRMED bookings on the same FULL ride: seats restored, status -> OPEN."""
    driver = await make_user(db_session, "cr_drv2", email_suffix="cancel")
    p1 = await make_user(db_session, "cr_pax2a", email_suffix="cancel")
    p2 = await make_user(db_session, "cr_pax2b", email_suffix="cancel")
    # Ride starts with 4 seats; two confirmed bookings already consumed 2 → simulate FULL
    ride = await make_ride(db_session, driver.user_id, seats=2, status=RideStatus.FULL)
    p_req = await make_passenger_request(db_session, p1.user_id)

    b1 = await make_booking(
        db_session, ride.ride_id, p1.user_id,
        status=BookingStatus.CONFIRMED, num_seats=1, request_id=p_req.request_id,
    )
    b2 = await make_booking(
        db_session, ride.ride_id, p2.user_id,
        status=BookingStatus.CONFIRMED, num_seats=1, request_id=p_req.request_id,
    )

    await PassengerService.cancel_request(db_session, p_req.request_id, p1.user_id)

    await db_session.refresh(ride)
    await db_session.refresh(b1)
    await db_session.refresh(b2)

    assert ride.available_seats == 4  # 2 + (1 + 1)
    assert ride.status == RideStatus.OPEN
    assert b1.status == BookingStatus.CANCELLED
    assert b2.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_request_confirmed_multi_ride_restores_each(db_session: AsyncSession):
    """Two CONFIRMED bookings across two rides — each ride is independently credited."""
    drv_a = await make_user(db_session, "cr_drvA", email_suffix="cancel")
    drv_b = await make_user(db_session, "cr_drvB", email_suffix="cancel")
    passenger = await make_user(db_session, "cr_paxAB", email_suffix="cancel")
    ride_a = await make_ride(db_session, drv_a.user_id, seats=3, status=RideStatus.OPEN)
    ride_b = await make_ride(db_session, drv_b.user_id, seats=1, status=RideStatus.FULL)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    b_a = await make_booking(
        db_session, ride_a.ride_id, passenger.user_id,
        status=BookingStatus.CONFIRMED, num_seats=1, request_id=p_req.request_id,
    )
    # Different passenger on ride_b to avoid unique_passenger_per_ride collision
    other = await make_user(db_session, "cr_pax_other", email_suffix="cancel")
    b_b = await make_booking(
        db_session, ride_b.ride_id, other.user_id,
        status=BookingStatus.CONFIRMED, num_seats=2, request_id=p_req.request_id,
    )

    await PassengerService.cancel_request(db_session, p_req.request_id, passenger.user_id)

    await db_session.refresh(ride_a)
    await db_session.refresh(ride_b)
    await db_session.refresh(b_a)
    await db_session.refresh(b_b)

    assert ride_a.available_seats == 4  # 3 + 1
    assert ride_a.status == RideStatus.OPEN
    assert ride_b.available_seats == 3  # 1 + 2
    assert ride_b.status == RideStatus.OPEN  # FULL -> OPEN
    assert b_a.status == BookingStatus.CANCELLED
    assert b_b.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_request_cancelled_ride_status_preserved(db_session: AsyncSession):
    """Ride that is already CANCELLED stays CANCELLED even though seats are credited."""
    driver = await make_user(db_session, "cr_drvC", email_suffix="cancel")
    passenger = await make_user(db_session, "cr_paxC", email_suffix="cancel")
    ride = await make_ride(db_session, driver.user_id, seats=2, status=RideStatus.CANCELLED)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    booking = await make_booking(
        db_session, ride.ride_id, passenger.user_id,
        status=BookingStatus.CONFIRMED, num_seats=1, request_id=p_req.request_id,
    )

    await PassengerService.cancel_request(db_session, p_req.request_id, passenger.user_id)

    await db_session.refresh(ride)
    await db_session.refresh(booking)

    assert ride.status == RideStatus.CANCELLED
    assert ride.available_seats == 3  # seat math still applied
    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_request_en_route_booking_restores_seats(db_session: AsyncSession):
    """EN_ROUTE counts as a seat-reserving status — must release seats on cancel."""
    driver = await make_user(db_session, "cr_drvD", email_suffix="cancel")
    passenger = await make_user(db_session, "cr_paxD", email_suffix="cancel")
    ride = await make_ride(db_session, driver.user_id, seats=1, status=RideStatus.FULL)
    p_req = await make_passenger_request(db_session, passenger.user_id)

    booking = await make_booking(
        db_session, ride.ride_id, passenger.user_id,
        status=BookingStatus.EN_ROUTE, num_seats=2, request_id=p_req.request_id,
    )

    await PassengerService.cancel_request(db_session, p_req.request_id, passenger.user_id)

    await db_session.refresh(ride)
    await db_session.refresh(booking)

    assert ride.available_seats == 3  # 1 + 2
    assert ride.status == RideStatus.OPEN
    assert booking.status == BookingStatus.CANCELLED
