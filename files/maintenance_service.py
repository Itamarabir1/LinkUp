"""
maintenance_service.py — תזמור תהליך התחזוקה.

עיקרון קריטי:
  commit → publish events (לא הפוך).
  אם publish נכשל — הנתונים כבר שמורים ב-DB. זה בסדר.
  אם DB נכשל — לא נשלחים events על נתונים שלא נשמרו.

publish_user_event הוא best-effort — כישלון Redis לא מפיל את התהליך.
"""
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.system.maintenance_crud import crud_maintenance
from app.domain.rides.broadcast import publish_user_event

logger = logging.getLogger(__name__)


class MaintenanceService:

    async def run_full_system_cleanup(self, db: AsyncSession) -> dict:
        """
        מריץ את כל עדכוני הסטטוס, עושה commit, ואז שולח WS events.
        הפרדה מכוונת: commit קודם, events אחר כך.
        """
        now = datetime.now()
        try:
            stats, pending_events = await crud_maintenance.bulk_update_expired_entities(db, now)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("❌ Maintenance cleanup failed: %s", e, exc_info=True)
            raise

        # publish events — אחרי commit, best-effort
        # כישלון Redis לא מבטל את עדכוני ה-DB
        for event in pending_events:
            try:
                await publish_user_event(event.user_id, event.event, event.extra)
            except Exception as e:
                logger.warning(
                    "Maintenance: publish_user_event failed user=%s event=%s: %s",
                    event.user_id,
                    event.event,
                    e,
                )

        logger.info(
            "✅ Maintenance finished. stats=%s events_published=%d",
            stats,
            len(pending_events),
        )
        return stats


maintenance_service = MaintenanceService()
