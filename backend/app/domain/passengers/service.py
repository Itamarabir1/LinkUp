import logging
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import IMMEDIATE_MATCH_LIMIT, PASSENGER_REQUESTS_DEFAULT_LIMIT, PASSENGER_REQUESTS_MAX_LIMIT
from app.core.exceptions.base import LinkUpError
from app.core.exceptions.booking import ForbiddenRideActionError, PassengerRequestNotFoundError
from app.core.exceptions.infrastructure import GeocodingError
from app.core.exceptions.ride import InvalidRideStatusError, RideNotFoundError
from app.core.exceptions.validation import BadRequestError
from app.core.pagination.cursor import CursorDecodeError, decode_cursor, encode_cursor
from app.domain.bookings.crud import crud_booking
from app.domain.passengers.crud import crud_passenger
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.schema import (
    PaginatedPassengerRequestsResponse,
    PassengerRequestCreate,
    PassengerRequestResponse,
    RideSearchRequest,
    RideSearchResponse,
)
from app.domain.rides.crud import crud_ride
from app.domain.rides.enum import RideStatus
from app.domain.rides.mapper import RideMapper
from app.domain.rides.schema import DriverInfoResponse, RideResponse
from app.infrastructure.geo.geocode_cache import get_coordinates

# Logger
logger = logging.getLogger(__name__)

_DEFAULT_SEARCH_RADIUS_KM = 1.0
_DEFAULT_SEARCH_RADIUS_M = 1000
_JERUSALEM = ZoneInfo("Asia/Jerusalem")


def jerusalem_calendar_day_utc_window(d: date) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of calendar day `d` in Asia/Jerusalem, as UTC."""
    start_local = datetime.combine(d, time.min, tzinfo=_JERUSALEM)
    end_exclusive_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_exclusive_local.astimezone(UTC)


def _radius_km_to_meters(radius_km: float | int | None) -> int:
    """
    API accepts kilometers; spatial queries run in meters.
    Backward compatibility: old clients may still send large meter-like values.
    """
    if radius_km is None:
        return _DEFAULT_SEARCH_RADIUS_M
    value = float(radius_km)
    if value > 100:
        return int(round(value))
    return int(round(value * 1000))


class PassengerService:
    @staticmethod
    async def create_passenger_request(db: AsyncSession, request_in: PassengerRequestCreate, passenger_id: UUID):
        """Create a passenger request and fetch immediate driver matches; passenger_id from auth token."""
        try:
            if request_in.pickup_lat is not None and request_in.pickup_lon is not None:
                p_lat, p_lon = request_in.pickup_lat, request_in.pickup_lon
            else:
                pickup_coords = await get_coordinates(request_in.pickup_name)
                if not pickup_coords:
                    raise GeocodingError(address=request_in.pickup_name or request_in.destination_name)
                p_lat, p_lon = pickup_coords

            dest_coords = await get_coordinates(request_in.destination_name)
            if not dest_coords:
                raise GeocodingError(address=request_in.pickup_name or request_in.destination_name)
            d_lat, d_lon = dest_coords

            new_request = await crud_passenger.create(db, request_in, p_lat, p_lon, d_lat, d_lon, passenger_id=passenger_id)
            await db.commit()

            # 3. Immediate driver matches (exclude rides owned by same user)
            matches, _ = await crud_passenger.find_rides_by_coordinates(
                db,
                p_lat,
                p_lon,
                d_lat,
                d_lon,
                _radius_km_to_meters(request_in.search_radius),
                limit=IMMEDIATE_MATCH_LIMIT,
                passenger_id=passenger_id,
            )

            # matching_rides: List[RideResponse] — find_rides returns (Ride, booking_status) tuples
            new_request.matching_rides = [
                RideResponse.model_validate(ride).model_copy(update={"user_booking_status": status}) for ride, status in matches
            ]
            return new_request

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in create_passenger_request: {e}")
            raise

    @staticmethod
    async def cancel_request(db: AsyncSession, request_id: UUID, passenger_id: UUID):
        """Cancel the request and release all related bookings (request owner only)."""
        p_req = await crud_passenger.get_by_id(db, request_id)
        if not p_req:
            raise PassengerRequestNotFoundError(request_id=str(request_id))

        # Auth: only request owner may cancel
        if p_req.passenger_id != passenger_id:
            raise ForbiddenRideActionError("גישה חסומה")

        # Bulk-cancel all bookings, restore seats on rides with active holds.
        # Single aggregate SELECT + per-affected-ride UPDATE + single bookings UPDATE.
        await crud_booking.bulk_cancel_bookings_for_request(db, request_id)

        p_req.status = PassengerStatus.CANCELLED

        await db.commit()
        return {"message": "הבקשה בוטלה וכל השריונים מול הנהגים שוחררו."}

    @staticmethod
    async def get_my_requests(
        db: AsyncSession,
        passenger_id: UUID,
        status: str | None = None,
        *,
        cursor: str | None = None,
        limit: int = PASSENGER_REQUESTS_DEFAULT_LIMIT,
    ) -> PaginatedPassengerRequestsResponse:
        """List passenger requests for the given user (cursor-paginated)."""
        status_enum = PassengerStatus(status) if status else None
        lim = max(1, min(limit, PASSENGER_REQUESTS_MAX_LIMIT))
        after: tuple[datetime, UUID] | None = None
        if cursor:
            try:
                after = decode_cursor(cursor)
            except CursorDecodeError as e:
                raise BadRequestError("מסמן עמוד לא תקין") from e
        rows = await crud_passenger.get_by_passenger_id(
            db,
            passenger_id,
            status_enum,
            limit=lim,
            after=after,
        )
        has_more = len(rows) > lim
        page_rows = rows[:lim]
        items = [PassengerRequestResponse.model_validate(r) for r in page_rows]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            next_cursor = encode_cursor(last.requested_departure_time, last.request_id)
        return PaginatedPassengerRequestsResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    async def get_matches_by_request_id(db: AsyncSession, request_id: UUID, current_user_id: UUID):
        """Fetch fresh ride matches for an existing passenger request."""
        p_req = await crud_passenger.get_by_id(db, request_id)
        if not p_req:
            raise PassengerRequestNotFoundError(request_id=str(request_id))
        if str(p_req.passenger_id) != str(current_user_id):
            raise ForbiddenRideActionError("גישה חסומה")

        try:
            origin_point = to_shape(p_req.pickup_geom)
            dest_point = to_shape(p_req.destination_geom)

            p_lat, p_lon = origin_point.y, origin_point.x
            d_lat, d_lon = dest_point.y, dest_point.x
        except Exception as e:
            logger.error(f"Error parsing coordinates for request {request_id}: {e}")
            raise GeocodingError(address=str(request_id))

        radius = getattr(p_req, "search_radius_meters", None) or getattr(p_req, "search_radius", _DEFAULT_SEARCH_RADIUS_M)
        matches, _ = await crud_passenger.find_rides_by_coordinates(
            db,
            p_lat,
            p_lon,
            d_lat,
            d_lon,
            radius,
            limit=IMMEDIATE_MATCH_LIMIT,
            passenger_id=p_req.passenger_id,
        )
        return matches

    @staticmethod
    async def search_rides_for_passenger(db: AsyncSession, search_data: RideSearchRequest):
        """Search open rides by geocoded addresses; does not persist a passenger request."""
        try:
            pickup_coords = await get_coordinates(search_data.pickup_name)
            dest_coords = await get_coordinates(search_data.destination_name)
            if not pickup_coords or not dest_coords:
                raise GeocodingError(address=search_data.pickup_name or search_data.destination_name)
            p_lat, p_lon = pickup_coords
            d_lat, d_lon = dest_coords

            radius = _radius_km_to_meters(getattr(search_data, "search_radius", None) or getattr(search_data, "radius", _DEFAULT_SEARCH_RADIUS_KM))
            destination_radius_m = _radius_km_to_meters(search_data.destination_radius) if search_data.destination_radius is not None else None
            after_tuple: tuple[datetime, UUID] | None = None
            if search_data.after:
                try:
                    after_tuple = decode_cursor(search_data.after)
                except CursorDecodeError as e:
                    raise LinkUpError(
                        message="מסמן עמוד חיפוש לא תקין",
                        status_code=422,
                        error_code="INVALID_SEARCH_CURSOR",
                    ) from e

            day_s = day_e = None
            range_s = range_e = None
            if search_data.departure_date is not None:
                day_s, day_e = jerusalem_calendar_day_utc_window(search_data.departure_date)
            elif search_data.departure_time is not None and search_data.departure_time_to is not None:
                range_s, range_e = search_data.departure_time, search_data.departure_time_to
            elif search_data.departure_time is not None:
                range_s = search_data.departure_time

            matches, has_more = await crud_passenger.find_rides_by_coordinates(
                db,
                p_lat,
                p_lon,
                d_lat,
                d_lon,
                radius,
                limit=search_data.limit,
                after=after_tuple,
                destination_radius_m=destination_radius_m,
                departure_day_start_utc=day_s,
                departure_day_end_exclusive_utc=day_e,
                departure_range_start=range_s,
                departure_range_end_inclusive=range_e,
                passenger_id=search_data.passenger_id,
                group_id=search_data.group_id,
            )

            items = []
            for ride, booking_status in matches:
                items.append(RideMapper.to_response(ride, user_booking_status=booking_status))
            next_cursor = None
            if has_more and items:
                last_ride = items[-1]
                next_cursor = encode_cursor(last_ride.departure_time, last_ride.ride_id)
            return RideSearchResponse(
                items=items,
                next_cursor=next_cursor,
                has_more=has_more,
            )

        except Exception as e:
            logger.error(f"Error in search_rides_for_passenger: {e}")
            raise

    @staticmethod
    async def get_all_rides_for_admin(db: AsyncSession, status: str = None):
        """List all rides with optional status filter (admin)."""
        return await crud_passenger.get_multi_rides(db, status=status)

    @staticmethod
    async def get_ride_driver_info(db: AsyncSession, ride_id: UUID) -> DriverInfoResponse:
        """Driver details for a ride (OPEN/FULL/ACTIVE only); 404 if missing or invalid."""
        ride = await crud_ride.get_with_driver(db, ride_id)
        if not ride:
            raise RideNotFoundError(ride_id)
        if ride.status not in (RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE):
            raise InvalidRideStatusError(ride.status.value, action="driver_info")
        driver = ride.driver
        if not driver:
            logger.error("Ride %s has no driver relation loaded", ride_id)
            raise LinkUpError(
                message="פרטי נהג לא זמינים לנסיעה זו",
                status_code=500,
                error_code="RIDE_DRIVER_MISSING",
            )
        return DriverInfoResponse(
            full_name=driver.full_name or "נהג",
            phone_number=getattr(driver, "phone_number", None),
        )

    @staticmethod
    async def create_passenger_request_for_ride_search(
        db: AsyncSession,
        passenger_id: UUID,
        pickup_name: str,
        destination_name: str,
        num_seats: int = 1,
    ):
        """Create a minimal PassengerRequest from join-from-search; returns row with request_id."""
        pickup_coords = await get_coordinates(pickup_name)
        dest_coords = await get_coordinates(destination_name)
        if not pickup_coords or not dest_coords:
            raise GeocodingError(address=pickup_name or destination_name)
        p_lat, p_lon = pickup_coords
        d_lat, d_lon = dest_coords
        request_in = PassengerRequestCreate(
            pickup_name=pickup_name,
            destination_name=destination_name,
            num_passengers=num_seats,
            search_radius=_DEFAULT_SEARCH_RADIUS_KM,
            is_notification_active=True,
            is_auto_generated=True,
        )
        return await crud_passenger.create(db, request_in, p_lat, p_lon, d_lat, d_lon, passenger_id=passenger_id)
