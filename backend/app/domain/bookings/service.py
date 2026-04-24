# app/domain/bookings/service.py
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.booking import (
    BookingAlreadyExistsError,
    BookingNotFoundError,
    ForbiddenRideActionError,
    NoSeatsAvailableError,
    PassengerRequestNotFoundError,
    RideNotAvailableError,
)
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.events.enum import DispatchTarget

# Events — outbox only
from app.domain.events.outbox import publish_to_outbox
from app.domain.notifications.constants import NotificationEvent
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.infrastructure.metrics import (
    bookings_approved_total,
    bookings_cancelled_total,
    bookings_created_total,
    bookings_rejected_total,
)
from app.infrastructure.redis.publisher import publish_user_event

logger = logging.getLogger(__name__)


class BookingService:
    @staticmethod
    async def request_to_join(
        db: AsyncSession,
        ride_id: UUID,
        request_id: UUID,
        num_seats: int = 1,
        current_user_id: UUID | None = None,
    ) -> Booking:
        """Create join request; outbox event notifies driver via worker."""
        try:
            ride = await crud_booking.get_ride_for_update(db, ride_id)
            if not ride or ride.status != RideStatus.OPEN:
                raise RideNotAvailableError(ride_id=str(ride_id))
            if await crud_booking.get_existing_booking_async(db, ride_id, request_id):
                raise BookingAlreadyExistsError(ride_id=str(ride_id), request_id=str(request_id))
            p_req = await db.get(PassengerRequest, request_id)
            if not p_req:
                raise PassengerRequestNotFoundError(request_id=str(request_id))
            if p_req.passenger_id != current_user_id:
                raise ForbiddenRideActionError("הבקשה אינה שייכת למשתמש המחובר")
            existing = await crud_booking.get_booking_by_ride_and_passenger_async(db, ride_id, p_req.passenger_id)
            if existing:
                if existing.status in (BookingStatus.CANCELLED, BookingStatus.REJECTED):
                    new_booking = await crud_booking.reuse_booking_after_rejection_or_cancellation(
                        db,
                        ride_id,
                        p_req.passenger_id,
                        request_id,
                        num_seats,
                    )
                else:
                    raise BookingAlreadyExistsError(ride_id=str(ride_id), request_id=str(request_id))
            else:
                new_booking = await crud_booking.create_booking_entry_async(db, ride_id, request_id, p_req.passenger_id, num_seats)
            await db.flush()
            await publish_to_outbox(
                db,
                NotificationEvent.PASSENGER_JOIN_REQUEST.value,
                {"booking_id": str(new_booking.booking_id)},
                [DispatchTarget.RABBITMQ.value],
            )
            logger.info(
                "[NOTIF] API: wrote to outbox event=booking.passenger_join_request booking_id=%s",
                new_booking.booking_id,
            )
            await db.commit()
            bookings_created_total.inc()
            await publish_user_event(
                ride.driver_id,
                "booking.passenger_join_request",
                {"booking_id": str(new_booking.booking_id), "ride_id": str(ride_id)},
            )
            # Reload booking with relationships loaded for proper serialization
            booking_with_relations = await crud_booking.get_async(db, new_booking.booking_id)
            return booking_with_relations or new_booking
        except (
            RideNotAvailableError,
            BookingAlreadyExistsError,
            PassengerRequestNotFoundError,
            ForbiddenRideActionError,
        ):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error in request_to_join: {e}")
            raise

    @staticmethod
    async def cancel_ride_and_all_bookings(db: AsyncSession, ride_id: UUID, driver_id: UUID) -> None:
        """
        Driver cancels entire ride and related bookings.
        Does not publish outbox — caller must emit domain events.
        """
        try:
            await crud_booking.cancel_ride_and_bookings(db, ride_id, driver_id)
            await db.commit()
        except ForbiddenRideActionError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to cancel ride {ride_id}: {e}")
            raise

    @staticmethod
    async def cancel_all_bookings_for_request(db: AsyncSession, request_id: UUID) -> None:
        """Cancel every booking tied to a passenger request (PassengerService hook)."""
        stmt = select(Booking).where(Booking.request_id == request_id)
        result = await db.execute(stmt)
        bookings = list(result.scalars().all())
        for b in bookings:
            await crud_booking.execute_booking_cancellation(db, b)
        await db.commit()

    @staticmethod
    async def get_booking(db: AsyncSession, booking_id: UUID) -> Booking:
        """Fetch single booking by id."""
        booking = await crud_booking.get_booking_by_id_async(db, booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id=str(booking_id))
        return booking

    @staticmethod
    async def approve_booking(db: AsyncSession, booking_id: UUID, driver_id: UUID) -> Booking:
        """Driver approves booking; outbox triggers passenger email/push."""
        try:
            booking = await crud_booking.get_booking_by_id_async(db, booking_id)
            if not booking:
                raise BookingNotFoundError(booking_id=str(booking_id))
            ride = booking.ride
            if not ride or ride.driver_id != driver_id:
                raise ForbiddenRideActionError("גישה חסומה")
            ride = await crud_booking.get_ride_for_update(db, booking.ride_id)
            if not ride:
                raise RideNotAvailableError(ride_id=str(booking.ride_id))
            await crud_booking.execute_booking_approval(db, booking)
            await db.flush()
            await publish_to_outbox(
                db,
                NotificationEvent.BOOKING_APPROVED_BY_DRIVER.value,
                {"booking_id": str(booking.booking_id)},
                [DispatchTarget.RABBITMQ.value],
            )
            await db.commit()
            bookings_approved_total.inc()
            await publish_user_event(
                booking.passenger_id,
                "booking.approved_by_driver",
                {"booking_id": str(booking_id), "ride_id": str(booking.ride_id)},
            )
            return await crud_booking.get_booking_by_id_async(db, booking_id)
        except (
            BookingNotFoundError,
            ForbiddenRideActionError,
            RideNotAvailableError,
            NoSeatsAvailableError,
        ):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error("approve_booking failed booking_id=%s: %s", booking_id, e)
            raise

    @staticmethod
    async def reject_booking(db: AsyncSession, booking_id: UUID, driver_id: UUID) -> Booking:
        """Driver rejects booking; outbox notifies passenger."""
        try:
            booking = await crud_booking.get_booking_by_id_async(db, booking_id)
            if not booking:
                raise BookingNotFoundError(booking_id=str(booking_id))
            ride = booking.ride
            if not ride or ride.driver_id != driver_id:
                raise ForbiddenRideActionError("גישה חסומה")
            await crud_booking.execute_booking_rejection(db, booking)
            await db.flush()
            await publish_to_outbox(
                db,
                NotificationEvent.BOOKING_REJECTED_BY_DRIVER.value,
                {"booking_id": str(booking.booking_id)},
                [DispatchTarget.RABBITMQ.value],
            )
            await db.commit()
            bookings_rejected_total.inc()
            await publish_user_event(
                booking.passenger_id,
                "booking.rejected_by_driver",
                {"booking_id": str(booking_id), "ride_id": str(booking.ride_id)},
            )
            return await crud_booking.get_booking_by_id_async(db, booking_id)
        except (BookingNotFoundError, ForbiddenRideActionError):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error("reject_booking failed booking_id=%s: %s", booking_id, e)
            raise

    @staticmethod
    async def cancel_booking(db: AsyncSession, booking_id: UUID, current_user_id: UUID) -> Booking:
        """Passenger or driver cancels booking (authorization checked)."""
        try:
            booking = await crud_booking.get_booking_by_id_async(db, booking_id)
            if not booking:
                raise BookingNotFoundError(booking_id=str(booking_id))
            ride = booking.ride
            is_passenger = booking.passenger_id == current_user_id
            is_driver = bool(ride and ride.driver_id == current_user_id)
            if not (is_passenger or is_driver):
                raise ForbiddenRideActionError("גישה חסומה")
            ride = await crud_booking.get_ride_for_update(db, booking.ride_id)
            if not ride:
                raise RideNotAvailableError(ride_id=str(booking.ride_id))
            await crud_booking.execute_booking_cancellation(db, booking)
            await db.flush()
            await db.commit()
            bookings_cancelled_total.inc()
            return await crud_booking.get_booking_by_id_async(db, booking_id)
        except (BookingNotFoundError, ForbiddenRideActionError, RideNotAvailableError):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error("cancel_booking failed booking_id=%s: %s", booking_id, e)
            raise


# Re-export for backward compatibility
from app.domain.bookings.booking_reads_service import BookingReadsService  # noqa: E402, F401, I001
from app.domain.bookings.location_service import BookingLocationService  # noqa: E402, F401, I001
