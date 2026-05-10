import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal  # ייבוא ה-sessionmaker האסינכרוני
from app.domain.system.outbox_service import OutboxService
from app.infrastructure.events.dispatcher.base import EventDispatcher
from app.infrastructure.outbox.listener import OutboxListener
from app.infrastructure.outbox.repository import OutboxRepository

logger = logging.getLogger("OutboxWorker")
FALLBACK_POLL_INTERVAL = 30.0


async def run_outbox_worker(dispatcher: EventDispatcher):
    service = OutboxService(repo=OutboxRepository(), dispatcher=dispatcher)
    listener: OutboxListener | None = OutboxListener()
    dsn = settings.DATABASE_URL_DIRECT

    try:
        try:
            await listener.connect(dsn)
            logger.info("[NOTIF] Outbox listener connected on channel outbox_new_event")
        except Exception as e:
            logger.warning(
                "LISTEN/NOTIFY unavailable: %s — falling back to 30s polling",
                e,
            )
            listener = None

        while True:
            try:
                if listener:
                    try:
                        await listener.wait_for_notify(timeout=FALLBACK_POLL_INTERVAL)
                    except Exception as wait_err:
                        logger.warning(
                            "LISTEN wait failed: %s — trying to reconnect and using fallback polling",
                            wait_err,
                        )
                        try:
                            await listener.close()
                        except Exception:
                            pass
                        try:
                            await listener.connect(dsn)
                            logger.info("[NOTIF] Outbox listener reconnected")
                        except Exception as reconnect_err:
                            logger.warning(
                                "LISTEN reconnect failed: %s — switching to polling mode",
                                reconnect_err,
                            )
                            listener = None
                else:
                    await asyncio.sleep(FALLBACK_POLL_INTERVAL)

                async with SessionLocal() as db:
                    events = await service.repo.get_pending_events(db, batch_size=50)

                for event in events:
                    try:
                        async with SessionLocal() as db:
                            await service.process_single_event(db, event)
                    except Exception as ex:
                        logger.exception("Event %s failed: %s", event.id, ex)

                if listener and events:
                    # Drain potential backlog that arrived while processing.
                    listener.wake()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.critical("Outbox loop error: %s", e)
                await asyncio.sleep(5.0)
    finally:
        if listener:
            await listener.close()
