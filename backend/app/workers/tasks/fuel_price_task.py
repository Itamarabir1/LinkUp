"""
Scans US EIA fuel prices — invoked from the scheduled queue.
Currently no persistence: only runs logic/API call; does not write to DB or Redis.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Seconds between fuel scans (86400 = daily; used by scheduled_tasks publisher)
FUEL_SCAN_INTERVAL = 86400


async def execute_fuel_scan_job():
    """
    Runs fuel price scan (called from scheduled-queue consumer).
    Currently does not persist data — only runs and logs.
    """
    try:
        if not settings.EIA_API_KEY:
            logger.warning("⛽ EIA_API_KEY missing – skipping fuel price scan")
        else:
            logger.info("⛽ Fuel price scan tick (no storage)")
    except Exception as e:
        logger.error("❌ Fuel price task failed: %s", e, exc_info=True)
        raise
