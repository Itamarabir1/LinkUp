"""בדיקה ש-publish_to_outbox כותב שורה ל-outbox_events באותה סשן."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.domain.events.outbox import publish_to_outbox
from app.infrastructure.outbox.model import OutboxEvent


@pytest.mark.asyncio
async def test_publish_to_outbox_persists_row(db_session: AsyncSession):
    await publish_to_outbox(db_session, "integration.test.event", {"ride_id": "abc"})
    await db_session.flush()

    result = await db_session.execute(select(OutboxEvent).where(OutboxEvent.event_name == "integration.test.event"))
    row = result.scalars().first()
    assert row is not None
    assert row.payload.get("ride_id") == "abc"
    assert row.status == "PENDING"
