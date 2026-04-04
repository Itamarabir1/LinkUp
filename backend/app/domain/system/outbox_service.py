import asyncio
import logging

from app.domain.events.enum import DispatchTarget
from app.infrastructure.outbox.repository import OutboxRepository
from app.infrastructure.events.dispatcher.base import EventDispatcher
from app.domain.events.schema import Event
from app.domain.events.routing import get_routing_metadata

logger = logging.getLogger(__name__)


class OutboxService:
    def __init__(self, repo: OutboxRepository, dispatcher: EventDispatcher):
        self.repo = repo
        self.dispatcher = dispatcher

    async def process_single_event(self, db, db_event):
        """
        הלוגיקה של 'איך מעבדים אירוע' נמצאת רק כאן.
        exchange + routing_key נגזרים מ-event_name (מקור אמת ב-domain.events.routing).
        """
        try:
            targets = [DispatchTarget(t) for t in (db_event.targets or []) if t]
            metadata = get_routing_metadata(db_event.event_name)
            event_dto = Event(
                name=db_event.event_name,
                payload=db_event.payload,
                targets=targets,
                metadata=metadata,
            )
            await asyncio.wait_for(self.dispatcher.dispatch(event_dto), timeout=5.0)
            await self.repo.mark_as_processed(db, db_event.id)
            await db.commit()
            logger.info(
                "[NOTIF] Outbox: processed event_id=%s event_name=%s",
                db_event.id,
                db_event.event_name,
            )
        except Exception as e:
            await db.rollback()
            await self.repo.increment_retries(db, db_event.id, error_msg=str(e))
            await db.commit()
            raise e
