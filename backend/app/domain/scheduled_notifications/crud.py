"""
CRUD לתזכורות מתוזמנות.

get_due — שולב partial index על deliver_at WHERE sent_at IS NULL.
           query קטן ויעיל — סורק רק רשומות שטרם נשלחו ועבר זמנן.
mark_sent — מסמן רשומה כנשלחה (sent_at = now).
create — כותב רשומה חדשה (נקרא מה-outbox worker).
"""

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

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
        """יוצר רשומת תזכורת. נקרא מה-outbox worker — לא מתוך core flow."""
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
        limit: int = 100,
    ) -> List[ScheduledNotification]:
        """
        שולף תזכורות שעבר זמנן וטרם נשלחו.
        מנצל את ה-partial index idx_scheduled_notifications_deliver.
        limit=100 — מגן מפני עומס בריצה בודדת.
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
        """מסמן תזכורת כנשלחה — sent_at = now()."""
        stmt = update(ScheduledNotification).where(ScheduledNotification.id == notification_id).values(sent_at=func.now())
        await db.execute(stmt)

    async def delete_by_ride(self, db: AsyncSession, ride_id: UUID) -> None:
        """
        מוחק תזכורות של נסיעה שבוטלה.
        ON DELETE CASCADE ב-DB מטפל בזה אוטומטית — זו פונקציה לשימוש ידני אם צריך.
        """
        from sqlalchemy import delete

        await db.execute(
            delete(ScheduledNotification).where(
                ScheduledNotification.ride_id == ride_id,
                ScheduledNotification.sent_at.is_(None),
            )
        )


crud_scheduled_notification = CRUDScheduledNotification()
