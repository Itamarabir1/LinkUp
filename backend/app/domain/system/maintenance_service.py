import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.system.maintenance_crud import crud_maintenance
from app.infrastructure.redis.publisher import publish_user_event
from app.core.config import settings

logger = logging.getLogger(__name__)


class MaintenanceService:
    async def run_full_system_cleanup(self, db: AsyncSession) -> dict:
        now = datetime.now()
        try:
            stats, pending_events = await crud_maintenance.bulk_update_expired_entities(db, now)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("❌ Maintenance cleanup failed: %s", e, exc_info=True)
            raise

        if settings.USER_EVENTS_ENABLED and pending_events:
            results = await asyncio.gather(
                *[publish_user_event(e.user_id, e.event, e.extra) for e in pending_events],
                return_exceptions=True,
            )
            failed = sum(1 for r in results if isinstance(r, Exception))
            if failed:
                logger.warning(
                    "Maintenance: %d/%d events failed to publish",
                    failed,
                    len(pending_events),
                )

        logger.info(
            "✅ Maintenance finished. stats=%s events=%d",
            stats,
            len(pending_events),
        )
        return stats


maintenance_service = MaintenanceService()
