from __future__ import annotations

from uuid import UUID
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import or_, text
from app.domain.bookings.model import Booking
from app.domain.rides.model import Ride
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.domain.bookings.enum import BookingStatus
from app.domain.passengers.enum import PassengerStatus
from app.core.exceptions.booking import NoSeatsAvailableError
from app.core.exceptions.booking import ForbiddenRideActionError
from sqlalchemy import select, func


class CRUDBooking:
    """
    אחריות: ניהול הגישה למסד הנתונים עבור ישות ההזמנות (Booking).
    מרכז את כל פונקציות השליפה והכתיבה שסופקו.
    """

    # --- שליפות (Queries) ---

    async def get_booking_by_id_async(self, db: AsyncSession, booking_id: UUID) -> Optional[Booking]:
        """Async variant של get_booking_by_id."""
        bid = UUID(str(booking_id)) if isinstance(booking_id, str) else booking_id
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Booking.passenger),
            )
            .where(Booking.booking_id == bid)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get(
        self,
        db: AsyncSession,
        *,
        id: Optional[UUID] = None,
        booking_id: Optional[UUID] = None,
    ) -> Optional[Booking]:
        """שליפה אסינכרונית להזמנה (לנוטיפיקציות). מקבל id= או booking_id=."""
        bid = id or booking_id
        if bid is None:
            return None
        return await self.get_booking_by_id_async(db, bid)

    async def get_async(self, db: AsyncSession, booking_id: UUID) -> Optional[Booking]:
        """שליפה אסינכרונית להזמנה עם טעינת יחסים (לשימוש ב-API endpoints)."""
        from app.domain.rides.model import Ride
        from app.domain.passengers.model import PassengerRequest

        bid = UUID(str(booking_id)) if isinstance(booking_id, str) else booking_id
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Booking.passenger),
            )
            .where(Booking.booking_id == bid)
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_ride_for_update(self, db: AsyncSession, ride_id: UUID) -> Optional[Ride]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Ride).where(Ride.ride_id == rid).with_for_update()
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_existing_booking_async(self, db: AsyncSession, ride_id: UUID, request_id: UUID) -> Optional[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        stmt = select(Booking).where(
            Booking.ride_id == rid,
            Booking.request_id == reqid,
            Booking.status != BookingStatus.CANCELLED,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_booking_by_ride_and_passenger_async(self, db: AsyncSession, ride_id: UUID, passenger_id: UUID) -> Optional[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        stmt = select(Booking).where(
            Booking.ride_id == rid,
            Booking.passenger_id == pid,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def reuse_booking_after_rejection_or_cancellation(
        self,
        db: AsyncSession,
        ride_id: UUID,
        passenger_id: UUID,
        request_id: UUID,
        num_seats: int,
    ) -> Optional[Booking]:
        """מעדכן booking קיים (CANCELLED/REJECTED) לבקשה חדשה – מאפשר 'בקשת הצטרפות מחדש' בלי להפר את unique_passenger_per_ride."""
        existing = await self.get_booking_by_ride_and_passenger_async(db, ride_id, passenger_id)
        if not existing or existing.status not in (
            BookingStatus.CANCELLED,
            BookingStatus.REJECTED,
        ):
            return None
        existing.request_id = request_id
        existing.num_seats = num_seats
        existing.status = BookingStatus.PENDING
        # העתקת פרטי תחנת העלייה מ-PassengerRequest
        p_req = await db.get(PassengerRequest, request_id)
        if p_req:
            p_req.status = PassengerStatus.MATCHED
            existing.pickup_name = p_req.pickup_name
            existing.pickup_point = p_req.pickup_geom
            existing.pickup_time = p_req.requested_departure_time
        await db.flush()
        return existing

    # --- פעולות כתיבה (Operations) ---

    async def create_booking_entry_async(
        self,
        db: AsyncSession,
        ride_id: UUID,
        request_id: UUID,
        passenger_id: UUID,
        num_seats: int,
    ) -> Booking:
        p_req = None
        if request_id:
            p_req = await db.get(PassengerRequest, request_id)
        pickup_time = p_req.requested_departure_time if p_req and p_req.requested_departure_time else None
        db_booking = Booking(
            ride_id=ride_id,
            request_id=request_id,
            passenger_id=passenger_id,
            num_seats=num_seats,
            status=BookingStatus.PENDING,
            pickup_name=p_req.pickup_name if p_req else None,
            pickup_point=p_req.pickup_geom if p_req else None,
            pickup_time=pickup_time,
        )
        db.add(db_booking)
        await db.flush()
        if request_id:
            await self.update_passenger_request_status_from_bookings(db, request_id)
        return db_booking

    async def execute_booking_approval(self, db: AsyncSession, booking: Booking):
        ride = booking.ride
        booking.status = BookingStatus.CONFIRMED

        # בדיקה כפולה — בין בקשה לאישור עוברים שעות/ימים,
        # יכול להיות שהמקום האחרון ניתן לנוסע אחר בינתיים
        if ride.available_seats < booking.num_seats:
            raise NoSeatsAvailableError("אין מקומות פנויים לאישור הזמנה זו")
        ride.available_seats -= booking.num_seats
        if ride.available_seats <= 0:
            ride.status = RideStatus.FULL

        # עדכון סטטוס PassengerRequest לפי כל ה-bookings
        if booking.request_id:
            await self.update_passenger_request_status_from_bookings(db, booking.request_id)

    async def execute_booking_rejection(self, db: AsyncSession, booking: Booking):
        booking.status = BookingStatus.REJECTED

        # עדכון סטטוס PassengerRequest לפי כל ה-bookings
        if booking.request_id:
            await self.update_passenger_request_status_from_bookings(db, booking.request_id)

    async def execute_booking_cancellation(self, db: AsyncSession, booking: Booking):
        if booking.status == BookingStatus.CONFIRMED:
            ride = booking.ride
            ride.available_seats += booking.num_seats
            if ride.status != RideStatus.CANCELLED:
                ride.status = RideStatus.OPEN

        booking.status = BookingStatus.CANCELLED

        # עדכון סטטוס PassengerRequest לפי כל ה-bookings
        if booking.request_id:
            await self.update_passenger_request_status_from_bookings(db, booking.request_id)

    async def cancel_all_bookings_for_ride(self, db: AsyncSession, ride_id: UUID):
        """
        ביטול רוחבי ומקצועי:
        1. מבטל את כל ההזמנות (Bookings) של הנסיעה.
        2. מחזיר את כל בקשות הנוסעים (PassengerRequests) לסטטוס PENDING.
        """
        from sqlalchemy import update as sa_update

        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Booking.request_id).where(Booking.ride_id == rid, Booking.request_id.isnot(None))
        result = await db.execute(stmt)
        request_ids = [r[0] for r in result.all()]
        if request_ids:
            await db.execute(
                sa_update(PassengerRequest).where(PassengerRequest.request_id.in_(request_ids)).values(status=PassengerStatus.ACTIVE.value)
            )
        await db.execute(sa_update(Booking).where(Booking.ride_id == rid).values(status=BookingStatus.CANCELLED.value))
        await db.execute(
            text("UPDATE rides SET status = CAST(:status AS ride_status), updated_at = now() WHERE ride_id = :ride_id"),
            {"status": RideStatus.CANCELLED.value, "ride_id": rid},
        )
        await db.flush()

    # --- פונקציות נוספות שנדרשות על ידי ה-BookingService ---

    async def get_user_bookings_count_async(self, db: AsyncSession, user_id: UUID, status_filter: Optional[str] = None) -> int:
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = select(func.count()).select_from(Booking).where(Booking.passenger_id == uid)
        if status_filter:
            stmt = stmt.where(Booking.status == status_filter)
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    async def get_user_bookings_filtered_async(
        self,
        db: AsyncSession,
        user_id: UUID,
        status_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Booking]:
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Booking.passenger),
            )
            .where(Booking.passenger_id == uid)
            .order_by(Booking.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status_filter:
            stmt = stmt.where(Booking.status == status_filter)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_bookings_with_relations(self, db: AsyncSession, user_id: UUID) -> List[Booking]:
        """הזמנות של הנוסע עם נסיעה ונהג (למסך התראות)."""
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .where(Booking.passenger_id == uid)
            .order_by(Booking.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_ride_bookings_by_status_async(self, db: AsyncSession, ride_id: UUID, booking_status: str) -> List[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Booking).where(Booking.ride_id == rid, Booking.status == booking_status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_pending_bookings_for_driver(self, db: AsyncSession, driver_id: UUID) -> List[Booking]:
        """כל הבקשות הממתינות לאישור עבור נסיעות של הנהג (למסך התראות)."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        stmt = (
            select(Booking)
            .join(Ride)
            .where(Ride.driver_id == did, Booking.status == BookingStatus.PENDING)
            .options(
                joinedload(Booking.ride),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .order_by(Booking.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_request_ids_for_ride(self, db: AsyncSession, ride_id: UUID) -> list:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Booking.request_id).where(Booking.ride_id == rid, Booking.request_id.isnot(None))
        result = await db.execute(stmt)
        return [r[0] for r in result.all()]

    async def bulk_update_bookings_status(self, db: AsyncSession, ride_id: UUID, new_status: BookingStatus):
        # Send enum value as plain string so PostgreSQL gets 'cancelled' not 'CANCELLED'
        status_val = new_status.value if hasattr(new_status, "value") else str(new_status)
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        await db.execute(
            text("UPDATE bookings SET status = CAST(:status AS booking_status), updated_at = now() WHERE ride_id = :ride_id"),
            {"status": status_val, "ride_id": rid},
        )

    async def cancel_ride_and_bookings(self, db: AsyncSession, ride_id: UUID, driver_id: UUID) -> list:
        """
        ביטול נסיעה על ידי נהג (לוגיקה אסינכרונית מלאה).
        - שומר הרשאות (רק נהג הנסיעה)
        - מבטל את כל ה-bookings של הנסיעה (CANCELLED)
        - מחשב מחדש סטטוס PassengerRequest לכל request_id של הנסיעה
        - מבטל את הנסיעה עצמה (Ride.status=cancelled)

        חשוב: אין כאן commit. ה-caller אחראי על commit/rollback.
        """
        stmt = select(Ride).where(Ride.ride_id == ride_id).with_for_update()
        result = await db.execute(stmt)
        ride = result.scalars().first()
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("אינך מורשה לבטל נסיעה זו")

        req_ids = await self.get_request_ids_for_ride(db, ride_id)

        await self.bulk_update_bookings_status(db, ride_id, BookingStatus.CANCELLED)

        # אחרי ביטול כל ה-bookings של הנסיעה, מחשבים מחדש סטטוס לכל בקשת נוסע
        # (כדי לא לדרוס סטטוס אם לאותה בקשה יש bookings נוספים על נסיעות אחרות)
        if req_ids:
            for rid in sorted(set([r for r in req_ids if r is not None])):
                await self.update_passenger_request_status_from_bookings(db, rid)

        ride.status = RideStatus.CANCELLED
        await db.flush()
        return req_ids

    async def bulk_update_requests_status(self, db: AsyncSession, request_ids: list, new_status: PassengerStatus):
        from sqlalchemy import update as sa_update

        status_value = new_status.value if hasattr(new_status, "value") else str(new_status)
        await db.execute(sa_update(PassengerRequest).where(PassengerRequest.request_id.in_(request_ids)).values(status=status_value))

    async def determine_passenger_request_status(self, db: AsyncSession, request_id: UUID) -> PassengerStatus:
        """
        קובע את הסטטוס המתאים של PassengerRequest לפי מצב ה-bookings שלו.
        """
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        result = await db.execute(select(Booking).where(Booking.request_id == reqid))
        bookings = result.scalars().all()

        if not bookings:
            return PassengerStatus.ACTIVE

        # בדיקה אם יש לפחות booking אחד מאושר
        has_confirmed = any(b.status == BookingStatus.CONFIRMED for b in bookings)
        if has_confirmed:
            # בדיקה אם כל ה-bookings הושלמו
            all_completed = all(b.status == BookingStatus.COMPLETED for b in bookings)
            if all_completed:
                return PassengerStatus.COMPLETED
            return PassengerStatus.APPROVED

        # בדיקה אם יש לפחות booking אחד ממתין לאישור
        has_pending = any(b.status == BookingStatus.PENDING for b in bookings)
        if has_pending:
            return PassengerStatus.PENDING

        # בדיקה אם כל ה-bookings נדחו
        all_rejected = all(b.status == BookingStatus.REJECTED for b in bookings)
        if all_rejected:
            return PassengerStatus.REJECTED

        # אם כל ה-bookings בוטלו או אין bookings פעילים
        return PassengerStatus.ACTIVE

    async def update_passenger_request_status_from_bookings(self, db: AsyncSession, request_id: UUID) -> None:
        """מעדכן את סטטוס ה-PassengerRequest לפי מצב ה-bookings שלו."""
        if not request_id:
            return
        from sqlalchemy import update as sa_update

        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        new_status = await self.determine_passenger_request_status(db, reqid)
        # צריך להעביר את ה-value של ה-enum, לא את האובייקט עצמו
        status_value = new_status.value if hasattr(new_status, "value") else str(new_status)
        await db.execute(sa_update(PassengerRequest).where(PassengerRequest.request_id == reqid).values(status=status_value))

    async def complete_bookings_by_ride_ids(self, db: AsyncSession, ride_ids: list):
        """מעדכן סטטוס לכל הבוקינגס ששייכים לרשימת נסיעות"""
        from sqlalchemy import update as sa_update

        await db.execute(
            sa_update(Booking)
            .where(
                Booking.ride_id.in_(ride_ids),
                Booking.status == BookingStatus.CONFIRMED,
            )
            .values(status=BookingStatus.COMPLETED.value)
        )

    # app/domain/bookings/crud.py

    # סוף הקובץ app/domain/bookings/crud.py

    async def get_user_history(self, db: AsyncSession, user_id: UUID, role: str) -> List[Booking]:
        # שימוש ב-joinedload כדי למנוע את בעיית ה-N+1 (שליפה יעילה)
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = select(Booking).options(joinedload(Booking.ride)).where(Booking.status != BookingStatus.CANCELLED)

        if role == "driver":
            stmt = stmt.join(Ride).where(Ride.driver_id == uid)
        elif role == "passenger":
            stmt = stmt.where(Booking.passenger_id == uid)
        else:
            stmt = stmt.join(Ride).where(or_(Ride.driver_id == uid, Booking.passenger_id == uid))

        result = await db.execute(stmt.order_by(Booking.created_at.desc()))
        return list(result.scalars().all())

crud_booking = CRUDBooking()
