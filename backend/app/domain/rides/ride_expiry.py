"""
לוגיקת סגירת נסיעות שזמנן עבר – לשימוש ב-Worker/תזמון.
מפריד מ-RideService כדי שה-service יישאר ממוקד בפעולות מול המשתמש (preview, create, cancel).
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.domain.rides.crud import crud_ride
from app.domain.bookings.crud import crud_booking
from app.domain.rides.enum import RideStatus
from app.domain.rides.broadcast import publish_ride_update

logger = logging.getLogger(__name__)


async def cleanup_expired_rides(db: Session) -> int:
    """
    סוגר נסיעות שזמנן עבר: מעדכן סטטוס ל-COMPLETED, משלים הזמנות קשורות, ומשדר לערוץ Realtime.
    מחזיר את מספר הנסיעות שנסוגו.
    """
    now = datetime.now()
    ride_ids = crud_ride.get_expired_ids(db, now)
    if not ride_ids:
        return 0

    try:
        crud_ride.bulk_set_completed(db, ride_ids)
        crud_booking.complete_bookings_by_ride_ids(db, ride_ids)

        for ride_id in ride_ids:
            await publish_ride_update(
                ride_id,
                {
                    "status": RideStatus.COMPLETED.value,
                    "event": "RIDE_FINISHED",
                },
            )

        db.commit()
        return len(ride_ids)
    except Exception as e:
        db.rollback()
        logger.error("Cleanup expired rides failed: %s", e)
        raise
