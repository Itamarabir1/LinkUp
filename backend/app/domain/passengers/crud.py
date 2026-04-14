"""
CRUD for passenger requests — single source of truth for persistence.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString
from sqlalchemy import and_, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.model import PassengerRequest
from app.domain.passengers.schema import PassengerRequestCreate
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride

logger = logging.getLogger(__name__)

# Relative window around min_departure_time for ride search (± hours)
_DEPARTURE_FLEXIBILITY_HOURS = 2
# Driver search along route — default radius (meters)
_FIND_PASSENGERS_ON_ROUTE_RADIUS_M = 2000
# New ride notification: origin/destination corridor radius + result cap
_RIDE_NOTIFICATION_RADIUS_DEST_M = 5000
_RIDE_NOTIFICATION_RADIUS_PICKUP_M = 2000
_RIDE_NOTIFICATION_PASSENGER_LIMIT = 200
_RIDE_DATE_WINDOW_DAYS_BEFORE = 1
_RIDE_DATE_WINDOW_DAYS_AFTER = 7
_GET_MULTI_RIDES_DEFAULT_LIMIT = 100


class CRUDPassenger:
    """
    All PassengerRequest DB access in one place (async + sync helpers).
    """

    # --- Reads ---

    async def get_by_id(self, db: AsyncSession, request_id: UUID) -> PassengerRequest | None:
        """Get request by primary key."""
        rid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        return await db.get(PassengerRequest, rid)

    async def get(self, db: AsyncSession, *, id: UUID) -> PassengerRequest | None:
        """get(db, id=...) style helper for notification handlers."""
        return await db.get(PassengerRequest, id)

    async def get_by_passenger_id(
        self,
        db: AsyncSession,
        passenger_id: UUID,
        status: PassengerStatus | None = None,
    ) -> list[PassengerRequest]:
        """List requests for a passenger (e.g. my-requests screen)."""
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        stmt = select(PassengerRequest).where(PassengerRequest.passenger_id == pid)
        if status is not None:
            stmt = stmt.where(PassengerRequest.status == status)
        stmt = stmt.order_by(PassengerRequest.requested_departure_time.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- Create ---

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
        """Insert new request; passenger_id comes from auth, not body."""
        req_time = request.requested_departure_time
        if req_time is None:
            req_time = datetime.now(UTC)
        # TIMESTAMPTZ accepts aware or naive datetimes
        db_request = PassengerRequest(
            passenger_id=passenger_id,
            num_passengers=request.num_passengers,
            group_id=request.group_id if hasattr(request, "group_id") else None,
            pickup_name=request.pickup_name,
            destination_name=request.destination_name,
            requested_departure_time=req_time,
            search_radius_meters=int(round(float(request.search_radius) * 1000)),
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

    # --- Ride search (passenger) ---

    async def find_rides_by_coordinates(
        self,
        db: AsyncSession,
        p_lat: float,
        p_lon: float,
        d_lat: float,
        d_lon: float,
        radius: int,
        limit: int | None = None,
        after_ride_id: UUID | None = None,
        min_departure_time: datetime | None = None,
        passenger_id: UUID | None = None,
        group_id: UUID | None = None,
    ) -> tuple[list[tuple[Ride, str | None]], bool]:
        """
        Spatial ride search near pickup/destination corridor.
        Ordered by departure_time, ride_id. Returns (rows, has_more); limit=None disables pagination.
        """
        pickup_geo = func.ST_SetSRID(func.ST_MakePoint(p_lon, p_lat), 4326)
        dest_geo = func.ST_SetSRID(func.ST_MakePoint(d_lon, d_lat), 4326)
        filters = and_(
            Ride.status.in_([RideStatus.OPEN, RideStatus.FULL]),
            Ride.available_seats > 0,
            Ride.group_id == group_id if group_id is not None else Ride.group_id.is_(None),
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
            func.ST_LineLocatePoint(cast(Ride.route_coords, Geometry), cast(pickup_geo, Geometry))
            < func.ST_LineLocatePoint(cast(Ride.route_coords, Geometry), cast(dest_geo, Geometry)),
        )
        if min_departure_time is not None:
            earliest = min_departure_time - timedelta(hours=_DEPARTURE_FLEXIBILITY_HOURS)
            latest = min_departure_time + timedelta(hours=_DEPARTURE_FLEXIBILITY_HOURS)
            filters = and_(
                filters,
                Ride.departure_time >= earliest,
                Ride.departure_time <= latest,
            )
        if after_ride_id is not None:
            after_ride = (await db.execute(select(Ride).where(Ride.ride_id == after_ride_id))).scalars().first()
            if after_ride is not None:
                filters = and_(
                    filters,
                    (
                        (Ride.departure_time > after_ride.departure_time)
                        | ((Ride.departure_time == after_ride.departure_time) & (Ride.ride_id > after_ride_id))
                    ),
                )
        stmt = (
            select(Ride, Booking.status.label("user_booking_status"))
            .outerjoin(
                Booking,
                and_(
                    Booking.ride_id == Ride.ride_id,
                    # passenger_id=None → join never matches → status NULL
                    Booking.passenger_id == passenger_id,
                    Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.REJECTED]),
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

        # Normalize Booking.status (enum or str) to str | None
        normalized: list[tuple[Ride, str | None]] = []
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

    # --- Passenger search (driver) ---

    async def find_passengers_on_route(
        self,
        db: AsyncSession,
        route_coords: list,
        radius_meters: int = _FIND_PASSENGERS_ON_ROUTE_RADIUS_M,
    ) -> list[PassengerRequest]:
        """Driver discovers passengers near their route polyline."""
        if not route_coords or len(route_coords) < 2:
            return []
        now = datetime.now()
        try:
            line = LineString([(p[1], p[0]) for p in route_coords])
            route_geom = from_shape(line, srid=4326)
            stmt = select(PassengerRequest).where(
                and_(
                    PassengerRequest.status == PassengerStatus.ACTIVE,
                    PassengerRequest.requested_departure_time > now,
                    func.ST_DWithin(
                        cast(PassengerRequest.pickup_geom, Geography),
                        cast(route_geom, Geography),
                        radius_meters,
                    ),
                ),
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
    ) -> list[PassengerRequest]:
        """Match passenger requests near driver's origin/destination pair."""
        now = datetime.now()
        driver_origin = func.ST_SetSRID(func.ST_MakePoint(origin_lon, origin_lat), 4326)
        driver_dest = func.ST_SetSRID(func.ST_MakePoint(dest_lon, dest_lat), 4326)
        stmt = select(PassengerRequest).where(
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
            ),
        )
        return list((await db.execute(stmt)).scalars().all())

    async def find_passengers_for_ride_notification(
        self,
        db: AsyncSession,
        ride: "Ride",
        radius_destination_m: int = _RIDE_NOTIFICATION_RADIUS_DEST_M,
        radius_pickup_m: int = _RIDE_NOTIFICATION_RADIUS_PICKUP_M,
        limit: int = _RIDE_NOTIFICATION_PASSENGER_LIMIT,
    ) -> list[PassengerRequest]:
        """
        Passenger targets for ride-created notifications.
        Filter pipeline: active + notifications on + same group scope + future window
        → exclude driver → dest proximity → pickup near route.
        """
        now = datetime.now()
        ride_date = ride.departure_time.date() if getattr(ride, "departure_time", None) else None
        if not ride_date:
            logger.warning(
                "find_passengers_for_ride_notification: no ride_date for ride_id=%s",
                getattr(ride, "ride_id", None),
            )
            return []
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

        min_date = ride_date - timedelta(days=_RIDE_DATE_WINDOW_DAYS_BEFORE)
        max_date = ride_date + timedelta(days=_RIDE_DATE_WINDOW_DAYS_AFTER)

        ride_group_id = getattr(ride, "group_id", None)
        group_match = PassengerRequest.group_id == ride_group_id if ride_group_id is not None else PassengerRequest.group_id.is_(None)

        stmt = (
            select(PassengerRequest)
            .where(
                and_(
                    PassengerRequest.status == PassengerStatus.ACTIVE,
                    PassengerRequest.is_notification_active.is_(True),
                    PassengerRequest.requested_departure_time > now,
                    func.date(PassengerRequest.requested_departure_time) >= min_date,
                    func.date(PassengerRequest.requested_departure_time) <= max_date,
                    PassengerRequest.passenger_id != driver_id,
                    group_match,
                    func.ST_DWithin(
                        cast(PassengerRequest.destination_geom, Geography),
                        cast(dest_geom, Geography),
                        radius_destination_m,
                    ),
                    func.ST_DWithin(
                        cast(PassengerRequest.pickup_geom, Geography),
                        cast(route_geom, Geography),
                        radius_pickup_m,
                    ),
                ),
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        passengers = list(result.scalars().all())
        logger.info(
            "find_passengers_for_ride_notification: ride_id=%s found %d passengers",
            getattr(ride, "ride_id", None),
            len(passengers),
        )
        return passengers

    # --- Rides for lists/UI ---

    async def get_multi_rides(
        self,
        db: AsyncSession,
        status: str | None = None,
        skip: int = 0,
        limit: int = _GET_MULTI_RIDES_DEFAULT_LIMIT,
    ) -> list[Ride]:
        """Admin-style ride listing with optional status filter."""
        stmt = select(Ride)
        if status:
            stmt = stmt.where(Ride.status == status)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # --- Maintenance ---

    def close_expired_requests(self, db: Session, now: datetime) -> int:
        """Expire active requests whose departure time passed; returns rows updated."""
        result = db.execute(
            update(PassengerRequest)
            .where(
                PassengerRequest.status == PassengerStatus.ACTIVE,
                PassengerRequest.requested_departure_time < now,
            )
            .values({PassengerRequest.status: PassengerStatus.EXPIRED.value}),
        )
        return result.rowcount or 0


# App-wide singleton
crud_passenger = CRUDPassenger()
