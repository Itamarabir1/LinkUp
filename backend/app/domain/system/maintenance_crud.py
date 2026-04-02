"""
maintenance_crud.py — עדכון סטטוסים פגי תוקף.

עיקרון: הפונקציות מחזירות רשימת events לשליחה — לא שולחות בעצמן.
        ה-MaintenanceService עושה commit ואז שולח את ה-events.
        כך נמנע race condition: events נשלחים רק אחרי commit מוצלח.

שימוש ב-RETURNING: UPDATE אטומי שמחזיר IDs בלי SELECT נוסף.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ProgrammingError

from app.domain.rides.model import Ride
from app.domain.passengers.model import PassengerRequest
from app.domain.bookings.model import Booking

logger = logging.getLogger(__name__)


@dataclass
class PendingUserEvent:
    """Event שממתין לשליחה אחרי commit."""

    user_id: UUID
    event: str
    extra: dict = field(default_factory=dict)


def _table_missing(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "does not exist" in msg or "undefinedtable" in msg or "undefined_table" in msg


class MaintenanceCRUD:
    """
    תחזוקה רוחבית — SQLAlchemy 2.0 async.
    מחזיר PendingUserEvent לשליחה אחרי commit — לא שולח Redis בעצמו.
    """

    async def bulk_update_expired_entities(self, db: AsyncSession, now: datetime) -> Tuple[dict, List[PendingUserEvent]]:
        """
        מריץ את כל עדכוני הסטטוס ומחזיר:
          - stats: מילון עם ספירות לכל entity
          - pending_events: רשימת events לשליחה אחרי commit
        """
        pending_events: List[PendingUserEvent] = []

        ride_rows, ride_events = await self._update_expired_rides(db, now)
        req_expired_rows, req_exp_events = await self._update_expired_passenger_requests(db, now)
        req_completed_rows, req_comp_events = await self._update_completed_passenger_requests(db, now)
        booking_rows, booking_events = await self._update_completed_bookings(db, now)

        pending_events.extend(ride_events)
        pending_events.extend(req_exp_events)
        pending_events.extend(req_comp_events)
        pending_events.extend(booking_events)

        stats = {
            "rides": len(ride_rows),
            "expired_requests": len(req_expired_rows),
            "completed_requests": len(req_completed_rows),
            "bookings": len(booking_rows),
        }
        return stats, pending_events

    async def _update_expired_rides(self, db: AsyncSession, now: datetime) -> Tuple[list, List[PendingUserEvent]]:
        """
        open → completed לנסיעות שעבר זמנן.
        RETURNING ride_id, driver_id — אטומי, ללא race condition.
        שולף גם passenger_ids של bookings confirmed לאותן נסיעות.
        """
        try:
            stmt = (
                update(Ride)
                .where(
                    Ride.departure_time <= now,
                    Ride.status == text("'open'::ride_status"),
                )
                .values(status=text("'completed'::ride_status"))
                .returning(Ride.ride_id, Ride.driver_id)
            )
            result = await db.execute(stmt)
            rows = result.all()

            if not rows:
                return [], []

            ride_ids = [r[0] for r in rows]

            # שליפת נוסעים confirmed לנסיעות שפגו
            passenger_stmt = select(Booking.ride_id, Booking.passenger_id).where(
                Booking.ride_id.in_(ride_ids),
                Booking.status == text("'confirmed'::booking_status"),
            )
            passenger_result = await db.execute(passenger_stmt)
            ride_passengers: dict = {}
            for ride_id, passenger_id in passenger_result.all():
                ride_passengers.setdefault(ride_id, []).append(passenger_id)

            events: List[PendingUserEvent] = []
            for ride_id, driver_id in rows:
                extra = {"ride_id": str(ride_id), "status": "completed"}
                events.append(PendingUserEvent(driver_id, "RIDE_FINISHED", extra))
                for passenger_id in ride_passengers.get(ride_id, []):
                    events.append(PendingUserEvent(passenger_id, "RIDE_FINISHED", extra))

            return rows, events

        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                logger.warning("Maintenance: table rides missing – skipping. %s", e)
                return [], []
            raise

    async def _update_expired_passenger_requests(self, db: AsyncSession, now: datetime) -> Tuple[list, List[PendingUserEvent]]:
        """active → expired לבקשות שעבר זמנן."""
        try:
            stmt = (
                update(PassengerRequest)
                .where(
                    PassengerRequest.requested_departure_time <= now,
                    PassengerRequest.status == text("'active'::passenger_request_status"),
                )
                .values(status=text("'expired'::passenger_request_status"))
                .returning(PassengerRequest.request_id, PassengerRequest.passenger_id)
            )
            result = await db.execute(stmt)
            rows = result.all()

            events = [
                PendingUserEvent(
                    passenger_id,
                    "REQUEST_EXPIRED",
                    {"request_id": str(request_id)},
                )
                for request_id, passenger_id in rows
            ]
            return rows, events

        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                logger.warning("Maintenance: table passenger_requests missing – skipping. %s", e)
                return [], []
            raise

    async def _update_completed_passenger_requests(self, db: AsyncSession, now: datetime) -> Tuple[list, List[PendingUserEvent]]:
        """matched → cancelled לבקשות שעבר זמנן."""
        try:
            stmt = (
                update(PassengerRequest)
                .where(
                    PassengerRequest.requested_departure_time <= now,
                    PassengerRequest.status == text("'matched'::passenger_request_status"),
                )
                .values(status=text("'cancelled'::passenger_request_status"))
                .returning(PassengerRequest.request_id, PassengerRequest.passenger_id)
            )
            result = await db.execute(stmt)
            rows = result.all()

            events = [
                PendingUserEvent(
                    passenger_id,
                    "REQUEST_EXPIRED",
                    {"request_id": str(request_id)},
                )
                for request_id, passenger_id in rows
            ]
            return rows, events

        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                return [], []
            raise

    async def _update_completed_bookings(self, db: AsyncSession, now: datetime) -> Tuple[list, List[PendingUserEvent]]:
        """confirmed → completed להזמנות של נסיעות שעבר זמנן."""
        try:
            subq = select(Ride.ride_id).where(Ride.departure_time <= now)
            stmt = (
                update(Booking)
                .where(
                    Booking.ride_id.in_(subq),
                    Booking.status == text("'confirmed'::booking_status"),
                )
                .values(status=text("'completed'::booking_status"))
                .returning(Booking.booking_id, Booking.passenger_id)
            )
            result = await db.execute(stmt)
            rows = result.all()

            events = [
                PendingUserEvent(
                    passenger_id,
                    "BOOKING_COMPLETED",
                    {"booking_id": str(booking_id)},
                )
                for booking_id, passenger_id in rows
            ]
            return rows, events

        except ProgrammingError as e:
            if _table_missing(e):
                await db.rollback()
                logger.warning("Maintenance: table bookings missing – skipping. %s", e)
                return [], []
            raise


crud_maintenance = MaintenanceCRUD()
