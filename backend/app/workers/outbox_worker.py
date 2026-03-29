import asyncio
import logging
from app.db.session import SessionLocal  # ייבוא ה-sessionmaker האסינכרוני
from app.infrastructure.outbox.repository import OutboxRepository
from app.infrastructure.events.dispatcher.base import EventDispatcher
from app.domain.system.outbox_service import OutboxService

logger = logging.getLogger("OutboxWorker")


async def run_outbox_worker(dispatcher: EventDispatcher, interval: float = 2.0):
    service = OutboxService(repo=OutboxRepository(), dispatcher=dispatcher)

    _poll_count = 0
    while True:
        try:
            _poll_count += 1
            async with SessionLocal() as db:
                events = await service.repo.get_pending_events(db, batch_size=50)
            if _poll_count % 30 == 0:
                n = len(events) if events else 0
                print(f"[NOTIF] Worker: poll #{_poll_count} -> {n} pending", flush=True)
                logger.info("[NOTIF] Outbox: poll #%s -> %s pending events", _poll_count, n)
            if events:
                logger.info("[NOTIF] Outbox: fetched %s pending event(s)", len(events))
                for e in events:
                    logger.info(
                        "[NOTIF] Outbox: processing event_id=%s event_name=%s",
                        e.id,
                        e.event_name,
                    )
                    try:
                        async with SessionLocal() as db:
                            await service.process_single_event(db, e)
                    except Exception as ex:
                        logger.exception("Outbox event %s failed: %s", e.id, ex)
        except Exception as e:
            logger.critical("🚨 Outbox Loop Error: %s", e)

        await asyncio.sleep(interval)
