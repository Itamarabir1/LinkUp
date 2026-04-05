"""Unit tests for NotificationHandler._fetch_source (scheduled reminder vs ride-only)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.notifications.core.handler import NotificationHandler
from app.domain.notifications.core.scheduled_reminder_source import ScheduledReminderSource


@pytest.mark.asyncio
async def test_fetch_source_scheduled_reminder_returns_wrapped_source() -> None:
    handler = NotificationHandler()
    ride = MagicMock()
    ride.ride_id = uuid4()
    sched_id = uuid4()
    user_id = uuid4()
    payload = {
        "scheduled_notification_id": str(sched_id),
        "user_id": str(user_id),
        "ride_id": str(ride.ride_id),
    }
    with patch(
        "app.domain.notifications.core.handler.crud_ride.get_for_notification",
        new_callable=AsyncMock,
        return_value=ride,
    ):
        out = await handler._fetch_source(MagicMock(), payload)
    assert isinstance(out, ScheduledReminderSource)
    assert out.ride is ride
    assert out.recipient_user_id == user_id
    assert out.scheduled_notification_id == sched_id


@pytest.mark.asyncio
async def test_fetch_source_ride_id_only_returns_ride() -> None:
    handler = NotificationHandler()
    ride = MagicMock()
    rid = uuid4()
    payload = {"ride_id": str(rid)}
    with patch(
        "app.domain.notifications.core.handler.crud_ride.get_for_notification",
        new_callable=AsyncMock,
        return_value=ride,
    ):
        out = await handler._fetch_source(MagicMock(), payload)
    assert out is ride
    assert not isinstance(out, ScheduledReminderSource)
