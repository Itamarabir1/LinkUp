import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BATCH_SIZE_DEFAULT
from app.infrastructure.outbox.model import OutboxEvent

logger = logging.getLogger(__name__)


class OutboxRepository:
    """
    Manages rows in the outbox table.
    Runs inside an existing transaction (ACID).
    """

    async def save_event(
        self,
        db: AsyncSession,
        event: OutboxEvent,  # full event object
    ) -> None:
        """
        Saves a pre-constructed outbox event.
        Transaction is managed by the Service layer.
        """
        try:
            # Add the ORM object to the session
            db.add(event)
            # Ensure default status (model or here)
            if not event.status:
                event.status = "PENDING"

            await db.flush()  # persist without commit (e.g. for generated ID)
            logger.info(
                "[NOTIF] Outbox repo: saved event_name=%s (in API process)",
                event.event_name,
            )
        except Exception as e:
            logger.error(f"❌ Failed to persist outbox event: {e!s}")
            # Could wrap in LinkUpError if desired
            raise

    async def get_pending_events(self, db: AsyncSession, batch_size: int = BATCH_SIZE_DEFAULT) -> list[OutboxEvent]:
        """
        Fetch pending events for the worker.
        skip_locked avoids contention across multiple server instances.
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
        Mark event processed with current timestamp.
        Direct in-place update for performance.
        """
        stmt = update(OutboxEvent).where(OutboxEvent.id == event_id).values(status="PROCESSED", processed_at=datetime.now(UTC))
        await db.execute(stmt)
        logger.info(f"✅ Event {event_id} marked as processed")

    async def increment_retries(self, db: AsyncSession, event_id: str, error_msg: str | None = None) -> None:
        """Increment retry_count and set last_error. Status stays PENDING for retry."""
        values = {"retry_count": OutboxEvent.retry_count + 1}
        if error_msg is not None:
            values["last_error"] = error_msg
        stmt = update(OutboxEvent).where(OutboxEvent.id == event_id).values(**values)
        await db.execute(stmt)
        logger.warning("Event %s retry incremented", event_id)

    async def mark_as_failed(self, db: AsyncSession, event_id: str, error_msg: str) -> None:
        """Record failure and set status FAILED."""
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
