import logging
from datetime import datetime
from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ProgrammingError

# ייבוא של כל המודלים הרלוונטיים במקום אחד
from app.domain.rides.model import Ride
from app.domain.passengers.model import PassengerRequest
from app.domain.bookings.model import Booking

logger = logging.getLogger(__name__)


def _table_missing(exc: BaseException) -> bool:
    """בודק אם השגיאה היא טבלה/relation לא קיימת (schema לא הורץ)."""
    msg = str(exc).lower()
    return "does not exist" in msg or "undefinedtable" in msg or "undefined_table" in msg


class MaintenanceCRUD:
    """
    תחזוקה רוחבית – תואם AsyncSession ו-SQLAlchemy 2.0 (select/update/execute).
    אם טבלה חסרה (schema לא הורץ), מדלג על השלב ומחזיר 0 – ה-worker לא קורס.
    """

    async def bulk_update_expired_entities(self, db: AsyncSession, now: datetime):
        """
        פונקציית תחזוקה רוחבית שמעדכנת את כל הישויות במערכת.
        כל שלב רץ בנפרד; אם טבלה לא קיימת – לוג + 0, בלי להפיל.
        """
        rides = await self._update_expired_rides(db, now)
        req_expired = await self._update_expired_passenger_requests(db, now)
        req_completed = await self._update_completed_passenger_requests(db, now)
        bookings = await self._update_completed_bookings(db, now)
        return rides, req_expired, req_completed, bookings

    async def _update_expired_rides(self, db: AsyncSession, now: datetime) -> int:
        try:
            stmt = (
                update(Ride)
                .where(
                    Ride.departure_time <= now,
                    Ride.status == text("'open'::ride_status"),
                )
                .values(status=text("'completed'::ride_status"))
            )
            res = await db.execute(stmt)
            return res.rowcount
        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                logger.warning(
                    "Maintenance: table rides missing or schema not applied – skipping. %s",
                    e,
                )
                return 0
            raise

    async def _update_expired_passenger_requests(self, db: AsyncSession, now: datetime) -> int:
        try:
            stmt = (
                update(PassengerRequest)
                .where(
                    PassengerRequest.requested_departure_time <= now,
                    PassengerRequest.status == text("'active'::passenger_request_status"),
                )
                .values(status=text("'expired'::passenger_request_status"))
            )
            res = await db.execute(stmt)
            return res.rowcount
        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                logger.warning(
                    "Maintenance: table passenger_requests missing – run db/schema.sql. %s",
                    e,
                )
                return 0
            raise

    async def _update_completed_passenger_requests(self, db: AsyncSession, now: datetime) -> int:
        try:
            stmt = (
                update(PassengerRequest)
                .where(
                    PassengerRequest.requested_departure_time <= now,
                    PassengerRequest.status == text("'matched'::passenger_request_status"),
                )
                .values(status=text("'cancelled'::passenger_request_status"))
            )
            res = await db.execute(stmt)
            return res.rowcount
        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                return 0
            raise

    async def _update_completed_bookings(self, db: AsyncSession, now: datetime) -> int:
        try:
            subq = select(Ride.ride_id).where(Ride.departure_time <= now)
            stmt = (
                update(Booking)
                .where(
                    Booking.ride_id.in_(subq),
                    Booking.status == text("'confirmed'::booking_status"),
                )
                .values(status=text("'completed'::booking_status"))
            )
            res = await db.execute(stmt)
            return res.rowcount
        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                logger.warning("Maintenance: table bookings missing – run db/schema.sql. %s", e)
                return 0
            raise


crud_maintenance = MaintenanceCRUD()
