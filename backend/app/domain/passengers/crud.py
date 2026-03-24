"""
CRUD לבקשות נוסעים – מקור אמת יחיד, API עקבי.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography, Geometry
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString

from app.domain.passengers.model import PassengerRequest
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.schema import PassengerRequestCreate
from app.domain.rides.model import Ride
from app.domain.rides.enum import RideStatus
from app.domain.bookings.model import Booking
from app.domain.bookings.enum import BookingStatus

logger = logging.getLogger(__name__)


class CRUDPassenger:
    """
    ניהול גישה לבקשות נוסעים (PassengerRequest).
    כל הפעולות תחת מחלקה אחת – אין פונקציות מפוזרות.
    """

    # --- שליפה ---

    async def get_by_id(
        self, db: AsyncSession, request_id: UUID
    ) -> Optional[PassengerRequest]:
        """שליפת בקשה לפי request_id (AsyncSession)."""
        rid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        return await db.get(PassengerRequest, rid)

    async def get(self, db: AsyncSession, *, id: UUID) -> Optional[PassengerRequest]:
        """שליפת בקשה לפי request_id (AsyncSession – לשימוש ב־handler). חתימה: get(db, id=...)."""
        return await db.get(PassengerRequest, id)

    async def get_by_passenger_id(
        self,
        db: AsyncSession,
        passenger_id: UUID,
        status: Optional[PassengerStatus] = None,
    ) -> List[PassengerRequest]:
        """שליפת בקשות לפי נוסע (למסך 'הבקשות שלי')."""
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        stmt = select(PassengerRequest).where(
            PassengerRequest.passenger_id == pid
        )
        if status is not None:
            stmt = stmt.where(PassengerRequest.status == status)
        stmt = stmt.order_by(PassengerRequest.requested_departure_time.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- יצירה ---

    async def create(
        self,
        db: AsyncSession,
        request: PassengerRequestCreate,
        p_lat: float,
        p_lon: float,
        d_lat: float,
        d_lon: float,
        passenger_id: UUID,
    ) -> PassengerRequest:
        """יצירת בקשה חדשה. passenger_id מהשרת (טוקן), לא מהגוף."""
        from datetime import timezone

        req_time = request.requested_departure_time
        if req_time is None:
            req_time = datetime.now(timezone.utc)
        # עמודה TIMESTAMP WITH TIME ZONE – מקבלת aware או naive
        db_request = PassengerRequest(
            passenger_id=passenger_id,
            num_passengers=request.num_passengers,
            group_id=request.group_id if hasattr(request, "group_id") else None,
            pickup_name=request.pickup_name,
            destination_name=request.destination_name,
            requested_departure_time=req_time,
            search_radius_meters=request.search_radius,
            is_auto_generated=request.is_auto_generated,
            is_notification_active=request.is_notification_active,
            pickup_geom=func.ST_SetSRID(func.ST_MakePoint(p_lon, p_lat), 4326),
            destination_geom=func.ST_SetSRID(func.ST_MakePoint(d_lon, d_lat), 4326),
            status=PassengerStatus.ACTIVE,
        )
        db.add(db_request)
        await db.flush()
        await db.refresh(db_request)
        return db_request

    # --- חיפוש נסיעות עבור נוסע ---

    async def find_rides_by_coordinates(
        self,
        db: AsyncSession,
        p_lat: float,
        p_lon: float,
        d_lat: float,
        d_lon: float,
        radius: int,
        limit: int | None = None,
        after_ride_id: Optional[UUID] = None,
        min_departure_time: Optional[datetime] = None,
        passenger_id: Optional[UUID] = None,
    ) -> tuple[List[tuple[Ride, Optional[str]]], bool]:
        """
        מנוע חיפוש נסיעות לפי קואורדינטות ורדיוס. מיון קבוע: departure_time.asc(), ride_id.asc().
        מחזיר (רשימה, has_more). אם limit=None מחזיר את כל התוצאות ו-has_more=False.
        """
        pickup_geo = func.ST_SetSRID(func.ST_MakePoint(p_lon, p_lat), 4326)
        dest_geo = func.ST_SetSRID(func.ST_MakePoint(d_lon, d_lat), 4326)
        filters = and_(
            Ride.status.in_([RideStatus.OPEN, RideStatus.FULL]),
            Ride.available_seats > 0,
            func.ST_DWithin(
                cast(Ride.route_coords, Geography),
                cast(pickup_geo, Geography),
                radius,
            ),
            func.ST_DWithin(
                cast(Ride.route_coords, Geography),
                cast(dest_geo, Geography),
                radius,
            ),
            func.ST_LineLocatePoint(
                cast(Ride.route_coords, Geometry), cast(pickup_geo, Geometry)
            )
            < func.ST_LineLocatePoint(
                cast(Ride.route_coords, Geometry), cast(dest_geo, Geometry)
            ),
        )
        if min_departure_time is not None:
            from datetime import timedelta
            FLEXIBILITY_HOURS = 2
            earliest = min_departure_time - timedelta(hours=FLEXIBILITY_HOURS)
            latest = min_departure_time + timedelta(hours=FLEXIBILITY_HOURS)
            filters = and_(
                filters,
                Ride.departure_time >= earliest,
                Ride.departure_time <= latest,
            )
        if after_ride_id is not None:
            after_ride = (
                await db.execute(select(Ride).where(Ride.ride_id == after_ride_id))
            ).scalars().first()
            if after_ride is not None:
                filters = and_(
                    filters,
                    (
                        (Ride.departure_time > after_ride.departure_time)
                        | (
                            (Ride.departure_time == after_ride.departure_time)
                            & (Ride.ride_id > after_ride_id)
                        )
                    ),
                )
        stmt = (
            select(Ride, Booking.status.label("user_booking_status"))
            .outerjoin(
                Booking,
                and_(
                    Booking.ride_id == Ride.ride_id,
                    # אם passenger_id=None → join condition לא יתאים → status יהיה NULL
                    Booking.passenger_id == passenger_id,
                    Booking.status.notin_(
                        [BookingStatus.CANCELLED, BookingStatus.REJECTED]
                    ),
                ),
            )
            .where(filters)
            .order_by(Ride.departure_time.asc(), Ride.ride_id.asc())
        )
        if passenger_id is not None:
            stmt = stmt.where(Ride.driver_id != passenger_id)
        if limit is not None:
            stmt = stmt.limit(limit + 1)
        rows = (await db.execute(stmt)).all()

        # נורמליזציה: Booking.status יכול להגיע כ-enum או string, רוצים str|None
        normalized: List[tuple[Ride, Optional[str]]] = []
        for ride, status in rows:
            if status is None:
                normalized.append((ride, None))
            elif hasattr(status, "value"):
                normalized.append((ride, str(status.value)))
            else:
                normalized.append((ride, str(status)))

        if limit is None:
            return (normalized, False)
        has_more = len(normalized) > limit
        items = normalized[:limit]
        return (items, has_more)

    # --- חיפוש נוסעים עבור נהג ---

    async def find_passengers_on_route(
        self,
        db: AsyncSession,
        route_coords: list,
        radius_meters: int = 2000,
    ) -> List[PassengerRequest]:
        """נהג מחפש נוסעים לאורך המסלול שלו."""
        if not route_coords or len(route_coords) < 2:
            return []
        now = datetime.now()
        try:
            line = LineString([(p[1], p[0]) for p in route_coords])
            route_geom = from_shape(line, srid=4326)
            stmt = (
                select(PassengerRequest)
                .where(
                    and_(
                        PassengerRequest.status == PassengerStatus.ACTIVE,
                        PassengerRequest.requested_departure_time > now,
                        func.ST_DWithin(
                            cast(PassengerRequest.pickup_geom, Geography),
                            cast(route_geom, Geography),
                            radius_meters,
                        ),
                    )
                )
            )
            return list((await db.execute(stmt)).scalars().all())
        except Exception as e:
            logger.error("Error searching passengers on route: %s", e)
            return []

    async def find_passengers_by_start_end(
        self,
        db: AsyncSession,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        radius: int,
    ) -> List[PassengerRequest]:
        """חיפוש נוסעים לפי מוצא ויעד של נהג."""
        now = datetime.now()
        driver_origin = func.ST_SetSRID(func.ST_MakePoint(origin_lon, origin_lat), 4326)
        driver_dest = func.ST_SetSRID(func.ST_MakePoint(dest_lon, dest_lat), 4326)
        stmt = (
            select(PassengerRequest)
            .where(
                and_(
                    PassengerRequest.status == PassengerStatus.ACTIVE,
                    PassengerRequest.requested_departure_time > now,
                    func.ST_DWithin(
                        cast(PassengerRequest.pickup_geom, Geography),
                        cast(driver_origin, Geography),
                        radius,
                    ),
                    func.ST_DWithin(
                        cast(PassengerRequest.destination_geom, Geography),
                        cast(driver_dest, Geography),
                        radius,
                    ),
                )
            )
        )
        return list((await db.execute(stmt)).scalars().all())

    def find_passengers_for_ride_notification(
        self,
        db: Session,
        ride: "Ride",
        radius_destination_m: int = 5000,
        radius_pickup_m: int = 2000,
        limit: int = 200,
    ) -> List[PassengerRequest]:
        """
        נוסעים רלוונטיים להתראה על נסיעה חדשה.
        סדר פילטרים: סטטוס+זמן (אינדקס) → לא הנהג → אופט-אין → יעד 5km → מוצא על המסלול.
        """
        now = datetime.now()
        ride_date = (
            ride.departure_time.date()
            if getattr(ride, "departure_time", None)
            else None
        )
        if not ride_date:
            logger.warning(
                "find_passengers_for_ride_notification: no ride_date for ride_id=%s",
                getattr(ride, "ride_id", None),
            )
            return []

        # שימוש ב-route_coords ישירות מהמסד (לא המרה לרשימה וחזרה) – כמו ב-find_rides_by_coordinates
        route_geom = getattr(ride, "route_coords", None)
        if not route_geom:
            logger.warning(
                "find_passengers_for_ride_notification: no route_coords for ride_id=%s",
                getattr(ride, "ride_id", None),
            )
            return []

        driver_id = getattr(ride, "driver_id", None)
        dest_geom = getattr(ride, "destination_geom", None)
        if not dest_geom:
            logger.warning(
                "find_passengers_for_ride_notification: no destination_geom for ride_id=%s",
                getattr(ride, "ride_id", None),
            )
            return []

        # חישוב טווח תאריכים גמיש (עד 7 ימים קדימה, עד יום אחד אחורה)
        min_date = ride_date - timedelta(days=1)
        max_date = ride_date + timedelta(days=7)

        # ספירת נוסעים לפני סינון גיאוגרפי (לדיבוג). רק ACTIVE — ביטול בקשה = CANCELLED ולא נשלחת התראה.
        total_active = (
            db.query(PassengerRequest)
            .filter(
                PassengerRequest.status == PassengerStatus.ACTIVE,
                PassengerRequest.requested_departure_time > now,
                func.date(PassengerRequest.requested_departure_time) <= max_date,
                func.date(PassengerRequest.requested_departure_time) >= min_date,
                PassengerRequest.passenger_id != driver_id,
            )
            .count()
        )
        logger.info(
            "find_passengers_for_ride_notification: ride_id=%s, ride_date=%s, date_range=[%s, %s], total_active_passengers=%d (before geo filter)",
            getattr(ride, "ride_id", None),
            ride_date,
            min_date,
            max_date,
            total_active,
        )

        # מוצא הנוסע חייב להיות במרחק עד 2 ק"מ מהמסלול של הנסיעה (route). רק ACTIVE — ביטול = CANCELLED.
        q = (
            db.query(PassengerRequest)
            .filter(
                PassengerRequest.status == PassengerStatus.ACTIVE,
                PassengerRequest.requested_departure_time > now,
                func.date(PassengerRequest.requested_departure_time) <= max_date,
                func.date(PassengerRequest.requested_departure_time) >= min_date,
                PassengerRequest.passenger_id != driver_id,
                # יעד בטווח של 5 ק"מ מהיעד של הנסיעה
                func.ST_DWithin(
                    cast(PassengerRequest.destination_geom, Geography),
                    cast(dest_geom, Geography),
                    radius_destination_m,
                ),
                # מוצא הנוסע: במרחק עד 2 ק"מ מהמסלול של הנסיעה בלבד
                func.ST_DWithin(
                    cast(PassengerRequest.pickup_geom, Geography),
                    cast(route_geom, Geography),
                    radius_pickup_m,
                ),
            )
            .limit(limit)
        )
        results = q.all()
        logger.info(
            "find_passengers_for_ride_notification: ride_id=%s, found %d matching passengers after all filters",
            getattr(ride, "ride_id", None),
            len(results),
        )
        if results:
            logger.info(
                "find_passengers_for_ride_notification: matching passenger_ids=%s",
                [r.passenger_id for r in results],
            )
        return results

    # --- נסיעות (שליפה לצורך UI/רשימות) ---

    async def get_multi_rides(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Ride]:
        """שליפת רשימת נסיעות עם סינון אופציונלי לפי סטטוס."""
        stmt = select(Ride)
        if status:
            stmt = stmt.where(Ride.status == status)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- תחזוקה ---

    def close_expired_requests(self, db: Session, now: datetime) -> int:
        """סגירת בקשות שזמן היציאה עבר ולא שובצו. מחזיר מספר רשומות שעודכנו."""
        result = db.execute(
            update(PassengerRequest)
            .where(
                PassengerRequest.status == PassengerStatus.ACTIVE,
                PassengerRequest.requested_departure_time < now,
            )
            .values({PassengerRequest.status: PassengerStatus.EXPIRED.value})
        )
        return result.rowcount or 0


# Singleton לשימוש באפליקציה
crud_passenger = CRUDPassenger()
