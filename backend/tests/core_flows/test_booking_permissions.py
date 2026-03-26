from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.core.exceptions.booking import ForbiddenRideActionError
from app.domain.bookings.service import BookingService

from tests.helpers.db_factories import make_passenger_request, make_ride, make_user


@pytest.mark.asyncio
async def test_request_to_join_rejects_non_owner_request(db_session: AsyncSession):
    """משתמש לא יכול להצטרף עם request_id שלא שייך לו."""
    driver = await make_user(db_session, "driver", email_suffix="permissions")
    passenger = await make_user(db_session, "passenger", email_suffix="permissions")
    attacker = await make_user(db_session, "attacker", email_suffix="permissions")
    ride = await make_ride(db_session, driver.user_id)
    passenger_request = await make_passenger_request(db_session, passenger.user_id)

    with patch(
        "app.domain.bookings.service.publish_to_outbox",
        new_callable=AsyncMock,
    ) as mock_publish:
        with pytest.raises(ForbiddenRideActionError):
            await BookingService.request_to_join(
                db_session,
                ride.ride_id,
                passenger_request.request_id,
                num_seats=1,
                current_user_id=attacker.user_id,
            )

    mock_publish.assert_not_awaited()
