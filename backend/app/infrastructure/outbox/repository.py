import logging
from datetime import UTC, datetime, timezone
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BATCH_SIZE_DEFAULT
from app.infrastructure.outbox.model import OutboxEvent

logger = logging.getLogger(__name__)


class OutboxRepository:
    """
    אחראי על ניהול הרישומים בטבלת ה-Outbox.
    פועל כחלק מטרנזקציה קיימת (ACID).
    """

    async def save_event(
        self,
        db: AsyncSession,
        event: OutboxEvent,  # מקבל אובייקט שלם
    ) -> None:
        """
        Saves a pre-constructed outbox event.
        Transaction is managed by the Service layer.
        """
        try:
            # פשוט מוסיפים את האובייקט לסשן
            db.add(event)
            # וודא שהסטטוס ברירת מחדל מוגדר (או במודל או כאן)
            if not event.status:
                event.status = "PENDING"

            await db.flush()  # דוחף ל-DB בלי Commit כדי לקבל ID אם צריך
            print(f"[NOTIF] Outbox repo: saved event_name={event.event_name}", flush=True)
            logger.info(
                "[NOTIF] Outbox repo: saved event_name=%s (in API process)",
                event.event_name,
            )
        except Exception as e:
            logger.error(f"❌ Failed to persist outbox event: {e!s}")
            # כאן תוכל לעטוף ב-LinkupError אם תרצה
            raise

    async def get_pending_events(self, db: AsyncSession, batch_size: int = BATCH_SIZE_DEFAULT) -> list[OutboxEvent]:
        """
        שליפת אירועים לעיבוד עבור ה-Worker.
        שימוש ב-skip_locked מונע התנגשויות בין מספר מופעים של השרת.
        """
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def mark_as_processed(self, db: AsyncSession, event_id: str) -> None:
        """
        מעדכן את האירוע כמעובד עם חותמת זמן של 'עכשיו'.
        ביצוע עדכון ישיר (In-place update) לטובת ביצועים מקסימליים.
        """
        stmt = update(OutboxEvent).where(OutboxEvent.id == event_id).values(status="PROCESSED", processed_at=datetime.now(UTC))
        await db.execute(stmt)
        logger.info(f"✅ Event {event_id} marked as processed")

    async def increment_retries(self, db: AsyncSession, event_id: str, error_msg: str | None = None) -> None:
        """מעלה מונה נסיונות ומעדכן last_error. לא משנה סטטוס (נשאר PENDING לניסיון חוזר)."""
        values = {"retry_count": OutboxEvent.retry_count + 1}
        if error_msg is not None:
            values["last_error"] = error_msg
        stmt = update(OutboxEvent).where(OutboxEvent.id == event_id).values(**values)
        await db.execute(stmt)
        logger.warning("Event %s retry incremented", event_id)

    async def mark_as_failed(self, db: AsyncSession, event_id: str, error_msg: str) -> None:
        """מתעד תקלה ומסמן FAILED."""
        stmt = (
            update(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .values(
                status="FAILED",
                last_error=error_msg,
                retry_count=OutboxEvent.retry_count + 1,
            )
        )
        await db.execute(stmt)
