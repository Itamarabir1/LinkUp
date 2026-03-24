from __future__ import annotations

from uuid import UUID
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from sqlalchemy import or_, text
from app.domain.bookings.model import Booking
from app.domain.rides.model import Ride
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.domain.bookings.enum import BookingStatus
from app.domain.passengers.enum import PassengerStatus
from app.core.exceptions.booking import NoSeatsAvailableError
from app.core.exceptions.booking import ForbiddenRideActionError
from sqlalchemy import and_, select, func


class CRUDBooking:
    """
    אחריות: ניהול הגישה למסד הנתונים עבור ישות ההזמנות (Booking).
    מרכז את כל פונקציות השליפה והכתיבה שסופקו.
    """

    # --- שליפות (Queries) ---

    def get_booking_by_id(self, db: Session, booking_id: UUID) -> Optional[Booking]:
        """עדכון שליפת בוקינג בודד (למשל לאישור הזמנה) – עם ride, driver, passenger_request, user, passenger (User)."""
        bid = UUID(str(booking_id)) if isinstance(booking_id, str) else booking_id
        return (
            db.query(Booking)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Booking.passenger),
            )
            .filter(Booking.booking_id == bid)
            .first()
        )

    async def get_booking_by_id_async(
        self, db: AsyncSession, booking_id: UUID
    ) -> Optional[Booking]:
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

    async def get_bookings_for_reminders(self, db, start, end):
        # הקוד שכתבנו קודם עם ה-select...
        pass

    def get_bookings_by_ride(self, db: Session, ride_id: UUID) -> List[Booking]:
        """עדכון שליפת כל הבוקינגס של נסיעה (למשל לביטול נסיעה ע"י נהג)"""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        return (
            db.query(Booking)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .filter(
                Booking.ride_id == rid, Booking.status == BookingStatus.CONFIRMED
            )
            .all()
        )

    def get_ride_for_update(self, db: Session, ride_id: UUID) -> Optional[Ride]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        return db.query(Ride).filter(Ride.ride_id == rid).with_for_update().first()

    async def get_existing_booking_async(
        self, db: AsyncSession, ride_id: UUID, request_id: UUID
    ) -> Optional[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        stmt = select(Booking).where(
            Booking.ride_id == rid,
            Booking.request_id == reqid,
            Booking.status != BookingStatus.CANCELLED,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    def get_existing_booking(
        self, db: Session, ride_id: UUID, request_id: UUID
    ) -> Optional[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        return (
            db.query(Booking)
            .filter(
                Booking.ride_id == rid,
                Booking.request_id == reqid,
                Booking.status != BookingStatus.CANCELLED,
            )
            .first()
        )

    async def get_booking_by_ride_and_passenger_async(
        self, db: AsyncSession, ride_id: UUID, passenger_id: UUID
    ) -> Optional[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        stmt = select(Booking).where(
            Booking.ride_id == rid,
            Booking.passenger_id == pid,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    def get_booking_by_ride_and_passenger(
        self, db: Session, ride_id: UUID, passenger_id: UUID
    ) -> Optional[Booking]:
        """בודק אם כבר קיימת הזמנה (כל סטטוס) לאותה נסיעה ולאותו נוסע – למניעת כפילות (unique_passenger_per_ride)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        return (
            db.query(Booking)
            .filter(
                Booking.ride_id == rid,
                Booking.passenger_id == pid,
            )
            .first()
        )

    def reuse_booking_after_rejection_or_cancellation(
        self,
        db: Session,
        ride_id: UUID,
        passenger_id: UUID,
        request_id: UUID,
        num_seats: int,
    ) -> Optional[Booking]:
        """מעדכן booking קיים (CANCELLED/REJECTED) לבקשה חדשה – מאפשר 'בקשת הצטרפות מחדש' בלי להפר את unique_passenger_per_ride."""
        existing = self.get_booking_by_ride_and_passenger(db, ride_id, passenger_id)
        if not existing or existing.status not in (
            BookingStatus.CANCELLED,
            BookingStatus.REJECTED,
        ):
            return None
        existing.request_id = request_id
        existing.num_seats = num_seats
        existing.status = BookingStatus.PENDING
        # העתקת פרטי תחנת העלייה מ-PassengerRequest
        p_req = db.get(PassengerRequest, request_id)
        if p_req:
            p_req.status = PassengerStatus.MATCHED
            existing.pickup_name = p_req.pickup_name
            existing.pickup_point = p_req.pickup_geom
            existing.pickup_time = p_req.requested_departure_time
        db.flush()
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
        pickup_time = (
            p_req.requested_departure_time
            if p_req and p_req.requested_departure_time
            else None
        )
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
            await db.run_sync(self.update_passenger_request_status_from_bookings, request_id)
        return db_booking

    def create_booking_entry(
        self,
        db: Session,
        ride_id: UUID,
        request_id: UUID,
        passenger_id: UUID,
        num_seats: int,
    ) -> Booking:
        # טעינת PassengerRequest כדי להעתיק את פרטי תחנת העלייה
        p_req = None
        if request_id:
            p_req = db.get(PassengerRequest, request_id)

        # יצירת Booking עם העתקת פרטי תחנת העלייה מ-PassengerRequest (עמודה עם timezone – מקבל aware/naive)
        pickup_time = (
            p_req.requested_departure_time
            if p_req and p_req.requested_departure_time
            else None
        )
        db_booking = Booking(
            ride_id=ride_id,
            request_id=request_id,
            passenger_id=passenger_id,
            num_seats=num_seats,
            status=BookingStatus.PENDING,
            # העתקת פרטי תחנת העלייה מ-PassengerRequest
            pickup_name=p_req.pickup_name if p_req else None,
            pickup_point=p_req.pickup_geom if p_req else None,
            pickup_time=pickup_time,
        )
        db.add(db_booking)
        db.flush()  # צריך flush לפני עדכון הסטטוס כדי שה-booking יהיה ב-DB

        # עדכון סטטוס PassengerRequest לפי כל ה-bookings (כולל החדש)
        if request_id:
            self.update_passenger_request_status_from_bookings(db, request_id)

        return db_booking

    def execute_booking_approval(self, db: Session, booking: Booking):
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
            self.update_passenger_request_status_from_bookings(db, booking.request_id)

    def execute_booking_rejection(self, db: Session, booking: Booking):
        booking.status = BookingStatus.REJECTED

        # עדכון סטטוס PassengerRequest לפי כל ה-bookings
        if booking.request_id:
            self.update_passenger_request_status_from_bookings(db, booking.request_id)

    def execute_booking_cancellation(self, db: Session, booking: Booking):
        if booking.status == BookingStatus.CONFIRMED:
            ride = booking.ride
            ride.available_seats += booking.num_seats
            if ride.status != RideStatus.CANCELLED:
                ride.status = RideStatus.OPEN

        booking.status = BookingStatus.CANCELLED

        # עדכון סטטוס PassengerRequest לפי כל ה-bookings
        if booking.request_id:
            self.update_passenger_request_status_from_bookings(db, booking.request_id)

    def cancel_all_bookings_for_ride(self, db: Session, ride_id: UUID):
        """
        ביטול רוחבי ומקצועי:
        1. מבטל את כל ההזמנות (Bookings) של הנסיעה.
        2. מחזיר את כל בקשות הנוסעים (PassengerRequests) לסטטוס PENDING.
        """
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        target_request_ids = (
            db.query(Booking.request_id)
            .filter(Booking.ride_id == rid, Booking.request_id.isnot(None))
            .all()
        )

        request_ids = [r[0] for r in target_request_ids]

        if request_ids:
            db.query(PassengerRequest).filter(
                PassengerRequest.request_id.in_(request_ids)
            ).update(
                {PassengerRequest.status: PassengerStatus.ACTIVE.value},
                synchronize_session="fetch",
            )

        db.query(Booking).filter(Booking.ride_id == rid).update(
            {Booking.status: BookingStatus.CANCELLED.value}, synchronize_session="fetch"
        )

        db.query(Ride).filter(Ride.ride_id == rid).update(
            {Ride.status: RideStatus.CANCELLED.value}, synchronize_session="fetch"
        )

        db.flush()

    # --- פונקציות נוספות שנדרשות על ידי ה-BookingService ---

    async def get_user_bookings_count_async(
        self, db: AsyncSession, user_id: UUID, status_filter: Optional[str] = None
    ) -> int:
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = select(func.count()).select_from(Booking).where(Booking.passenger_id == uid)
        if status_filter:
            stmt = stmt.where(Booking.status == status_filter)
        result = await db.execute(stmt)
        return int(result.scalar() or 0)

    def get_user_bookings_count(
        self, db: Session, user_id: UUID, status_filter: Optional[str] = None
    ) -> int:
        """ספירת הזמנות של משתמש (לפי פילטר אופציונלי)."""
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        q = db.query(func.count()).select_from(Booking).filter(Booking.passenger_id == uid)
        if status_filter:
            q = q.filter(Booking.status == status_filter)
        return q.scalar() or 0

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

    def get_user_bookings_filtered(
        self,
        db: Session,
        user_id: UUID,
        status_filter: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> List[Booking]:
        """שליפת הזמנות של משתמש עם offset/limit (לפי passenger_id וסטטוס אופציונלי)."""
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        query = (
            db.query(Booking)
            .options(
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Booking.passenger),
            )
            .filter(Booking.passenger_id == uid)
        )
        if status_filter:
            query = query.filter(Booking.status == status_filter)
        return (
            query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()
        )

    def get_user_bookings_with_relations(
        self, db: Session, user_id: UUID
    ) -> List[Booking]:
        """הזמנות של הנוסע עם נסיעה ונהג (למסך התראות)."""
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        return (
            db.query(Booking)
            .filter(Booking.passenger_id == uid)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .order_by(Booking.created_at.desc())
            .all()
        )

    async def get_ride_bookings_by_status_async(
        self, db: AsyncSession, ride_id: UUID, booking_status: str
    ) -> List[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Booking).where(
            Booking.ride_id == rid, Booking.status == booking_status
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    def get_ride_bookings_by_status(
        self, db: Session, ride_id: UUID, booking_status: str
    ) -> List[Booking]:
        """שליפת הזמנות עבור נסיעה ספציפית לפי סטטוס"""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        return (
            db.query(Booking)
            .filter(Booking.ride_id == rid, Booking.status == booking_status)
            .all()
        )

    def get_all_pending_bookings_for_driver(
        self, db: Session, driver_id: UUID
    ) -> List[Booking]:
        """כל הבקשות הממתינות לאישור עבור נסיעות של הנהג (למסך התראות)."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        return (
            db.query(Booking)
            .join(Ride)
            .filter(
                Ride.driver_id == did,
                Booking.status == BookingStatus.PENDING,
            )
            .options(
                joinedload(Booking.ride),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .order_by(Booking.created_at.desc())
            .all()
        )

    def get_request_ids_for_ride(self, db: Session, ride_id: UUID) -> list:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        results = (
            db.query(Booking.request_id)
            .filter(Booking.ride_id == rid, Booking.request_id.isnot(None))
            .all()
        )
        return [r[0] for r in results]

    def bulk_update_bookings_status(
        self, db: Session, ride_id: UUID, new_status: BookingStatus
    ):
        # Send enum value as plain string so PostgreSQL gets 'cancelled' not 'CANCELLED'
        status_val = (
            new_status.value if hasattr(new_status, "value") else str(new_status)
        )
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        db.execute(
            text(
                "UPDATE bookings SET status = CAST(:status AS booking_status), updated_at = now() WHERE ride_id = :ride_id"
            ),
            {"status": status_val, "ride_id": rid},
        )

    def cancel_ride_and_bookings_sync(
        self, db: Session, ride_id: UUID, driver_id: UUID
    ) -> list:
        """
        ביטול נסיעה על ידי נהג (לוגיקה סינכרונית לריצה בתוך db.run_sync).
        - שומר הרשאות (רק נהג הנסיעה)
        - מבטל את כל ה-bookings של הנסיעה (CANCELLED)
        - מחשב מחדש סטטוס PassengerRequest לכל request_id של הנסיעה
        - מבטל את הנסיעה עצמה (Ride.status=cancelled)

        חשוב: אין כאן commit. ה-caller אחראי על commit/rollback.
        """
        ride = self.get_ride_for_update(db, ride_id)
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("אינך מורשה לבטל נסיעה זו")

        req_ids = self.get_request_ids_for_ride(db, ride_id)

        self.bulk_update_bookings_status(db, ride_id, BookingStatus.CANCELLED)

        # אחרי ביטול כל ה-bookings של הנסיעה, מחשבים מחדש סטטוס לכל בקשת נוסע
        # (כדי לא לדרוס סטטוס אם לאותה בקשה יש bookings נוספים על נסיעות אחרות)
        if req_ids:
            for rid in sorted(set([r for r in req_ids if r is not None])):
                self.update_passenger_request_status_from_bookings(db, rid)

        # PostgreSQL ride_status enum expects lowercase 'cancelled'; ORM would send enum name 'CANCELLED'
        db.execute(
            text(
                "UPDATE rides SET status = CAST(:status AS ride_status), updated_at = now() WHERE ride_id = :ride_id"
            ),
            {"status": RideStatus.CANCELLED.value, "ride_id": ride_id},
        )
        db.flush()
        return req_ids

    def bulk_update_requests_status(
        self, db: Session, request_ids: list, new_status: PassengerStatus
    ):
        status_value = (
            new_status.value if hasattr(new_status, "value") else str(new_status)
        )
        db.query(PassengerRequest).filter(
            PassengerRequest.request_id.in_(request_ids)
        ).update({PassengerRequest.status: status_value}, synchronize_session="fetch")

    def determine_passenger_request_status(
        self, db: Session, request_id: UUID
    ) -> PassengerStatus:
        """
        קובע את הסטטוס המתאים של PassengerRequest לפי מצב ה-bookings שלו.
        """
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        bookings = db.query(Booking).filter(Booking.request_id == reqid).all()

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

    def update_passenger_request_status_from_bookings(
        self, db: Session, request_id: UUID
    ) -> None:
        """מעדכן את סטטוס ה-PassengerRequest לפי מצב ה-bookings שלו."""
        if not request_id:
            return
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        new_status = self.determine_passenger_request_status(db, reqid)
        # צריך להעביר את ה-value של ה-enum, לא את האובייקט עצמו
        status_value = (
            new_status.value if hasattr(new_status, "value") else str(new_status)
        )
        db.query(PassengerRequest).filter(
            PassengerRequest.request_id == reqid
        ).update({PassengerRequest.status: status_value}, synchronize_session="fetch")

    def complete_bookings_by_ride_ids(self, db: Session, ride_ids: list):
        """מעדכן סטטוס לכל הבוקינגס ששייכים לרשימת נסיעות"""
        return (
            db.query(Booking)
            .filter(
                Booking.ride_id.in_(ride_ids), Booking.status == BookingStatus.CONFIRMED
            )
            .update(
                {"status": BookingStatus.COMPLETED.value}, synchronize_session=False
            )
        )

    # app/domain/bookings/crud.py

    # סוף הקובץ app/domain/bookings/crud.py

    def get_user_history(self, db: Session, user_id: UUID, role: str) -> List[Booking]:
        # שימוש ב-joinedload כדי למנוע את בעיית ה-N+1 (שליפה יעילה)
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        query = (
            db.query(Booking)
            .options(joinedload(Booking.ride))
            .filter(Booking.status != BookingStatus.CANCELLED)
        )

        if role == "driver":
            # תיקון: אנחנו צריכים את הנהג של הנסיעה
            query = query.join(Ride).filter(Ride.driver_id == uid)
        elif role == "passenger":
            query = query.filter(Booking.passenger_id == uid)
        else:
            query = query.join(Ride).filter(
                or_(Ride.driver_id == uid, Booking.passenger_id == uid)
            )

        return query.order_by(Booking.created_at.desc()).all()


# בתוך קלאס ה-CRUDBooking
async def get_bookings_for_reminders(
    self,
    db: AsyncSession,  # שים לב לסוג האסינכרוני
    start_window: datetime,
    end_window: datetime,
) -> List[Booking]:
    """
    שליפת כל ההזמנות המאושרות שזמן האיסוף שלהן חל בחלון הזמן המוגדר.

    Senior Implementation (Async 2.0):
    1. selectinload: הדרך המועדפת ב-Async לטעון יחסים (Relationships).
       זה מריץ שאילתה נוספת בצורה יעילה ומונע את שגיאת ה-DetachedInstanceError.
    2. Execution: שימוש ב-db.execute ו-scalars() כדי לקבל את האובייקטים עצמם.
    """

    # בניית השאילתה בסינטקס 2.0
    stmt = (
        select(Booking)
        .options(
            # טעינה אסינכרונית בטוחה של ישויות קשורות
            selectinload(Booking.passenger),
            selectinload(Booking.ride),
        )
        .where(
            and_(
                Booking.status == "confirmed",
                ~Booking.reminder_sent,
                Booking.pickup_time >= start_window,
                Booking.pickup_time <= end_window,
            )
        )
    )

    # הרצה אסינכרונית
    result = await db.execute(stmt)

    # החזרת כל התוצאות כרשימה של אובייקטי Booking
    return result.scalars().all()


crud_booking = CRUDBooking()
