"""
סורק מחירי דלק (EIA US) – מופעל מהתור המתוזמן.
כרגע בלי שמירה: רק מריץ את הלוגיקה/קריאת API; לא שומר ל־DB או Redis.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# מרווח בין סריקות (שניות). יומי = 86400 – משמש את המתזמן (scheduled_tasks)
FUEL_SCAN_INTERVAL = 86400


async def execute_fuel_scan_job():
    """
    ביצוע סריקת דלק (נקרא מה-consumer של התור המתוזמן).
    כרגע: לא שומר נתונים – רק מריץ ומתעד.
    """
    try:
        if not settings.EIA_API_KEY:
            logger.warning("⛽ EIA_API_KEY missing – skipping fuel price scan")
        else:
            logger.info("⛽ Fuel price scan tick (no storage)")
    except Exception as e:
        logger.error("❌ Fuel price task failed: %s", e, exc_info=True)
        raise
