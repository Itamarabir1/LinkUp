"""
CRUD for scheduled reminders.

get_due — uses partial index on deliver_at WHERE sent_at IS NULL.
           small efficient query — only due unsent rows.
mark_sent — marks a row sent (sent_at = now).
create — inserts a new row (called from outbox worker).
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.core.constants import BATCH_SIZE_DEFAULT
from app.domain.scheduled_notifications.model import ScheduledNotification

logger = logging.getLogger(__name__)


class CRUDScheduledNotification:
    async def create(
        self,
        db: AsyncSession,
        *,
        ride_id: UUID | None,
        user_id: UUID,
        type: str,
        deliver_at: datetime,
    ) -> ScheduledNotification:
        """Creates a reminder row. Called from outbox worker — not from core request flow."""
        obj = ScheduledNotification(
            ride_id=ride_id,
            user_id=user_id,
            type=type,
            deliver_at=deliver_at,
        )
        db.add(obj)
        await db.flush()
        return obj

    async def get_due(
        self,
        db: AsyncSession,
        now: datetime,
        limit: int = BATCH_SIZE_DEFAULT,
    ) -> list[ScheduledNotification]:
        """
        Fetches due reminders that have not been sent yet.
        Uses partial index idx_scheduled_notifications_deliver.
        BATCH_SIZE_DEFAULT caps work per run.
        """
        stmt = (
            select(ScheduledNotification)
            .where(
                ScheduledNotification.deliver_at <= now,
                ScheduledNotification.sent_at.is_(None),
            )
            .order_by(ScheduledNotification.deliver_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def mark_sent(self, db: AsyncSession, notification_id: UUID) -> None:
        """Marks a reminder as sent — sent_at = now()."""
        stmt = update(ScheduledNotification).where(ScheduledNotification.id == notification_id).values(sent_at=func.now())
        await db.execute(stmt)

    async def delete_by_ride(self, db: AsyncSession, ride_id: UUID) -> None:
        """
        Deletes reminders for a cancelled ride.
        ON DELETE CASCADE in the DB usually handles this — manual helper when needed.
        """
        await db.execute(
            delete(ScheduledNotification).where(
                ScheduledNotification.ride_id == ride_id,
                ScheduledNotification.sent_at.is_(None),
            ),
        )


crud_scheduled_notification = CRUDScheduledNotification()
