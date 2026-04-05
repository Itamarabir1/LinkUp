import logging

from app.db.session import SessionLocal
from app.domain.system.maintenance_service import maintenance_service

logger = logging.getLogger(__name__)


async def execute_maintenance_job(service=maintenance_service):
    """
    ביצוע תחזוקה (נקרא מה-consumer של התור המתוזמן).
    """
    async with SessionLocal() as db:
        logger.info("🛠️ Scheduler: Starting full system maintenance cleanup...")
        stats = await service.run_full_system_cleanup(db)
        logger.info("✅ Maintenance finished. Stats: %s", stats)
