# app/domain/bookings/location_service.py
"""GPS location broadcasting for active rides."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.booking import BookingNotFoundError, ForbiddenRideActionError
from app.core.exceptions.validation import BadRequestError
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.geo.schema import DriverLocationReport, LocationUpdate, PassengerLocationReport
from app.domain.rides.enum import RideStatus
from app.infrastructure.location.location_service import (
    broadcast_location_to_participants,
    broadcast_passenger_location_to_driver,
)


class BookingLocationService:
    @staticmethod
    async def broadcast_driver_location(
        db: AsyncSession,
        booking_id: UUID,
        driver_id: UUID,
        body: DriverLocationReport,
    ) -> None:
        """Validate driver + active ride, then broadcast GPS to confirmed passengers."""
        booking = await crud_booking.get_booking_by_id_async(db, booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id=str(booking_id))
        if not booking.ride:
            raise BookingNotFoundError(booking_id=str(booking_id))
        if str(booking.ride.driver_id) != str(driver_id):
            raise ForbiddenRideActionError("גישה חסומה – רק נהג הנסיעה יכול לדווח מיקום")
        if booking.ride.status != RideStatus.ACTIVE:
            raise BadRequestError("ניתן לדווח מיקום רק בנסיעה פעילה (active)")
        confirmed = await crud_booking.get_ride_bookings_by_status_async(db, booking.ride_id, BookingStatus.CONFIRMED)
        involved = [row.booking_id for row in confirmed]
        location_in = LocationUpdate(
            booking_id=0,
            lat=body.lat,
            lon=body.lng,
            heading=body.heading or 0.0,
            speed=body.speed or 0.0,
        )
        await broadcast_location_to_participants(location_in, booking.ride_id, involved)

    @staticmethod
    async def broadcast_passenger_location(
        db: AsyncSession,
        booking_id: UUID,
        passenger_id: UUID,
        body: PassengerLocationReport,
    ) -> None:
        """Validate booking ownership, then broadcast passenger GPS to driver channel."""
        booking = await crud_booking.get_booking_by_id_async(db, booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id=str(booking_id))
        if not booking.ride:
            raise BookingNotFoundError(booking_id=str(booking_id))
        if str(booking.passenger_id) != str(passenger_id):
            raise ForbiddenRideActionError("גישה חסומה – רק הנוסע של ההזמנה יכול לדווח מיקום")
        await broadcast_passenger_location_to_driver(
            ride_id=booking.ride_id,
            booking_id=booking.booking_id,
            passenger_id=passenger_id,
            lat=body.lat,
            lng=body.lng,
            heading=body.heading or 0.0,
            speed=body.speed or 0.0,
        )
