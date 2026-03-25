
import logging
from typing import List, Optional
from uuid import UUID

from geoalchemy2.shape import to_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.booking import PassengerRequestNotFoundError
from app.core.exceptions.infrastructure import GeocodingError
from app.domain.passengers.crud import crud_passenger
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.model import Booking
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.schema import (
    PassengerRequestCreate,
    PassengerRequestResponse,
    RideSearchRequest,
)
from app.domain.rides.crud import crud_ride
from app.domain.rides.enum import RideStatus
from app.domain.rides.mapper import RideMapper
from app.domain.rides.schema import DriverInfoResponse
from app.infrastructure.geo.client import geo_client

# הגדרת לוגר
logger = logging.getLogger(__name__)


class PassengerService:
    @staticmethod
    async def create_passenger_request(
        db: AsyncSession, request_in: PassengerRequestCreate, passenger_id: UUID
    ):
        """יוצר בקשה (מודעה) ומחפש נהגים תואמים מיד. passenger_id מהטוקן (API)."""
        try:
            if request_in.pickup_lat is not None and request_in.pickup_lon is not None:
                p_lat, p_lon = request_in.pickup_lat, request_in.pickup_lon
            else:
                p_lat, p_lon = await geo_client.fetch_coordinates(request_in.pickup_name)
            d_lat, d_lon = await geo_client.fetch_coordinates(request_in.destination_name)

            if p_lat is None or d_lat is None:
                raise GeocodingError(
                    address=request_in.pickup_name or request_in.destination_name
                )

            new_request = await crud_passenger.create(
                db, request_in, p_lat, p_lon, d_lat, d_lon, passenger_id=passenger_id
            )

            # 3. מציאת נהגים רלוונטיים באופן מיידי (לא כולל נסיעות של המשתמש עצמו)
            matches, _ = await crud_passenger.find_rides_by_coordinates(
                db, p_lat, p_lon, d_lat, d_lon, request_in.search_radius,
                passenger_id=passenger_id,
            )

            # הוספת התוצאות לאובייקט החוזר
            new_request.matching_rides = matches
            return new_request

        except Exception as e:
            logger.error(f"Error in create_passenger_request: {e}")
            raise

    @staticmethod
    async def cancel_request(
        db: AsyncSession, request_id: UUID, passenger_id: UUID
    ):
        """ביטול הבקשה ושחרור כל ההזמנות הקשורות אליה (רק לבעל הבקשה)."""
        p_req = await crud_passenger.get_by_id(db, request_id)
        if not p_req:
            raise PassengerRequestNotFoundError(request_id=str(request_id))

        # הרשאות: רק בעל הבקשה יכול לבטל
        if p_req.passenger_id != passenger_id:
            from app.core.exceptions.booking import ForbiddenRideActionError

            raise ForbiddenRideActionError("גישה חסומה")

        # 1. ביטול כל ההזמנות ושחרור מושבים
        bookings = list(
            (await db.execute(select(Booking).where(Booking.request_id == request_id)))
            .scalars()
            .all()
        )
        for b in bookings:
            await db.run_sync(
                lambda sess, booking=b: crud_booking.execute_booking_cancellation(
                    sess, booking
                )
            )

        # 2. עדכון סטטוס הבקשה עצמה (ביטול בקשה = CANCELLED, לא כיבוי התראות)
        p_req.status = PassengerStatus.CANCELLED

        await db.commit()
        return {"message": "הבקשה בוטלה וכל השריונים מול הנהגים שוחררו."}

    @staticmethod
    async def get_my_requests(
        db: AsyncSession,
        passenger_id: UUID,
        status: Optional[str] = None,
    ) -> List[PassengerRequestResponse]:
        """רשימת הבקשות שלי כנוסע (הבקשות שלי)."""
        status_enum = PassengerStatus(status) if status else None
        requests = await crud_passenger.get_by_passenger_id(
            db, passenger_id, status_enum
        )
        return [PassengerRequestResponse.model_validate(r) for r in requests]

    @staticmethod
    async def get_matches_by_request_id(db: AsyncSession, request_id: UUID):
        """שליפת התאמות חדשות לבקשה קיימת"""
        p_req = await crud_passenger.get_by_id(db, request_id)
        if not p_req:
            raise PassengerRequestNotFoundError(request_id=str(request_id))

        try:
            origin_point = to_shape(p_req.pickup_geom)
            dest_point = to_shape(p_req.destination_geom)

            p_lat, p_lon = origin_point.y, origin_point.x
            d_lat, d_lon = dest_point.y, dest_point.x
        except Exception as e:
            logger.error(f"Error parsing coordinates for request {request_id}: {e}")
            raise GeocodingError(address=str(request_id))

        radius = getattr(p_req, "search_radius_meters", None) or getattr(
            p_req, "search_radius", 1000
        )
        matches, _ = await crud_passenger.find_rides_by_coordinates(
            db, p_lat, p_lon, d_lat, d_lon, radius,
            passenger_id=p_req.passenger_id,
        )
        return matches

    @staticmethod
    async def search_rides_for_passenger(
        db: AsyncSession, search_data: RideSearchRequest
    ):
        """חיפוש נסיעות פעיל לפי קואורדינטות של כתובות. לא שומר בקשה ב-DB."""
        from app.domain.passengers.schema import RideSearchResponse

        try:
            p_lat, p_lon = await geo_client.fetch_coordinates(search_data.pickup_name)
            d_lat, d_lon = await geo_client.fetch_coordinates(search_data.destination_name)

            if p_lat is None or d_lat is None:
                raise GeocodingError(
                    address=search_data.pickup_name or search_data.destination_name
                )

            radius = getattr(search_data, "search_radius", None) or getattr(
                search_data, "radius", 1000
            )

            matches, has_more = await crud_passenger.find_rides_by_coordinates(
                db,
                p_lat,
                p_lon,
                d_lat,
                d_lon,
                radius,
                limit=search_data.limit,
                after_ride_id=search_data.after,
                min_departure_time=search_data.departure_time,
                passenger_id=search_data.passenger_id,
                group_id=search_data.group_id,
            )

            items = []
            for ride, booking_status in matches:
                items.append(
                    RideMapper.to_response(ride, user_booking_status=booking_status)
                )
            next_cursor = str(items[-1].ride_id) if has_more and items else None
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
        """שליפת כל הנסיעות עם פילטר אופציונלי (בתוך ה-Class)"""
        return await crud_passenger.get_multi_rides(db, status=status)

    @staticmethod
    async def get_ride_driver_info(
        db: AsyncSession, ride_id: UUID
    ) -> DriverInfoResponse:
        """פרטי נהג של נסיעה – רק לנסיעות פתוחות (OPEN/FULL). מחזיר 404 אם לא נמצא או לא רלוונטי."""
        ride = await db.run_sync(lambda sess: crud_ride.get_with_driver(sess, ride_id))
        if not ride:
            raise ValueError("נסיעה לא נמצאה")
        if ride.status not in (RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE):
            raise ValueError("הנסיעה אינה פתוחה להצטרפות")
        driver = ride.driver
        if not driver:
            raise ValueError("פרטי נהג לא זמינים")
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
        """יוצר PassengerRequest מינימלי מבקשת הצטרפות מחיפוש; מחזיר את הבקשה (עם request_id)."""
        p_lat, p_lon = await geo_client.fetch_coordinates(pickup_name)
        d_lat, d_lon = await geo_client.fetch_coordinates(destination_name)
        if p_lat is None or d_lat is None:
            raise GeocodingError(address=pickup_name or destination_name)
        request_in = PassengerRequestCreate(
            pickup_name=pickup_name,
            destination_name=destination_name,
            num_passengers=num_seats,
            search_radius=1000,
            is_notification_active=True,
            is_auto_generated=True,
        )
        return await crud_passenger.create(
            db, request_in, p_lat, p_lon, d_lat, d_lon, passenger_id=passenger_id
        )
