# app/domain/bookings/service.py
import logging
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions.booking import (
    BookingAlreadyExistsError,
    BookingNotFoundError,
    ForbiddenRideActionError,
    NoSeatsAvailableError,
    PassengerRequestNotFoundError,
    RideNotAvailableError,
)
from app.core.exceptions.validation import BadRequestError
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.bookings.schema import (
    BookingManifestItem,
    BookingResponse,
    DriverSummaryInfo,
    DriverSummaryResponse,
    NotificationItemResponse,
    PaginatedBookingsResponse,
    PassengerBookingSummaryItem,
    PassengerSummaryResponse,
    RideManifestResponse,
    RideWithPassengersItem,
)
from app.domain.events.enum import DispatchTarget

# Events — outbox only
from app.domain.events.outbox import publish_to_outbox
from app.domain.geo.schema import DriverLocationReport, LocationUpdate, PassengerLocationReport
from app.domain.notifications.constants import NotificationEvent
from app.domain.users.model import User
from app.infrastructure.location.location_service import (
    broadcast_location_to_participants,
    broadcast_passenger_location_to_driver,
)
from app.infrastructure.redis.publisher import publish_user_event

# Models & enums
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride

logger = logging.getLogger(__name__)


class BookingService:
    @staticmethod
    def _booking_to_manifest_item(booking: Booking) -> BookingManifestItem | None:
        """Shared manifest row for one booking (whatsapp/phone rules identical to driver manifest)."""
        user = booking.passenger_request.user if booking.passenger_request else None
        if not user:
            return None
        clean_phone = "".join(filter(str.isdigit, user.phone_number or ""))
        if clean_phone.startswith("0"):
            clean_phone = "972" + clean_phone[1:]
        whatsapp_link = f"https://wa.me/{clean_phone}?text={quote('היי, אני הנהג שלך מהאפליקציה')}"
        return BookingManifestItem(
            booking_id=booking.booking_id,
            passenger_id=user.user_id,
            passenger_name=user.full_name,
            phone=user.phone_number or "",
            whatsapp_link=whatsapp_link,
            num_seats=booking.num_seats,
            status=booking.status,
            pickup_name=booking.pickup_name,
            pickup_time=booking.pickup_time,
            destination_name=(booking.passenger_request.destination_name if booking.passenger_request else None),
        )

    @staticmethod
    def _driver_to_summary(driver: User | None) -> DriverSummaryInfo | None:
        """Map ride.driver to passenger-facing contact snippet (same fields as DriverInfoResponse)."""
        if not driver:
            return None
        return DriverSummaryInfo(
            full_name=driver.full_name or "נהג",
            phone_number=getattr(driver, "phone_number", None),
        )

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
    async def get_ride_manifest(db: AsyncSession, ride_id: UUID, driver_id: UUID) -> RideManifestResponse:
        """Driver manifest: pending + confirmed bookings with contact hints."""
        ride = await db.get(Ride, ride_id)
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("גישה חסומה")

        stmt = (
            select(Booking)
            .options(joinedload(Booking.passenger_request).joinedload(PassengerRequest.user))
            .where(
                Booking.ride_id == ride_id,
                Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value]),
            )
            .order_by(Booking.created_at.desc())
        )
        result = await db.execute(stmt)
        bookings = list(result.scalars().all())

        manifest_items: list[BookingManifestItem] = []
        for b in bookings:
            item = BookingService._booking_to_manifest_item(b)
            if item:
                manifest_items.append(item)

        available_seats_left = max(0, ride.available_seats)
        return RideManifestResponse(
            ride_id=ride_id,
            total_confirmed_passengers=len(manifest_items),
            available_seats_left=available_seats_left,
            passengers=manifest_items,
        )

    @staticmethod
    async def get_driver_summary(db: AsyncSession, driver_id: UUID) -> DriverSummaryResponse:
        """All driver rides with pending/confirmed passengers — single DB round-trip."""
        from app.domain.bookings.schema import DriverSummaryResponse, RideWithPassengersItem, BookingManifestItem
        from urllib.parse import quote

        rides = await crud_booking.get_driver_rides_with_passengers(db, driver_id)
        items = []
        for ride in rides:
            passengers = []
            for b in ride.bookings:
                user = b.passenger_request.user if b.passenger_request else None
                if not user:
                    continue
                clean_phone = "".join(filter(str.isdigit, user.phone_number or ""))
                if clean_phone.startswith("0"):
                    clean_phone = "972" + clean_phone[1:]
                passengers.append(BookingManifestItem(
                    booking_id=b.booking_id,
                    passenger_id=user.user_id,
                    passenger_name=user.full_name or "נוסע",
                    phone=user.phone_number or "",
                    whatsapp_link=f"https://wa.me/{clean_phone}?text={quote('היי, אני הנהג שלך מהאפליקציה')}",
                    num_seats=b.num_seats,
                    status=b.status,
                    pickup_name=b.pickup_name,
                    pickup_time=b.pickup_time,
                    destination_name=(b.passenger_request.destination_name if b.passenger_request else None),
                ))
            items.append(RideWithPassengersItem(
                    ride_id=ride.ride_id,
                    origin_name=ride.origin_name,
                    destination_name=ride.destination_name,
                    departure_time=ride.departure_time,
                    estimated_arrival_time=ride.estimated_arrival_time,
                    available_seats=ride.available_seats,
                    price=float(ride.price or 0),
                    status=ride.status.value if hasattr(ride.status, "value") else str(ride.status),
                    group_id=ride.group.group_id if ride.group else None,
                    group_name=ride.group.name if ride.group else None,
                    passengers=passengers,
                ))
        return DriverSummaryResponse(rides=items)

    @staticmethod
    async def get_passenger_summary(db: AsyncSession, passenger_id: UUID) -> PassengerSummaryResponse:
        """All passenger bookings with ride + driver info — single DB round-trip."""
        from app.domain.bookings.schema import PassengerSummaryResponse, PassengerBookingSummaryItem, DriverSummaryInfo

        bookings = await crud_booking.get_passenger_bookings_with_rides(db, passenger_id)
        items = []
        for b in bookings:
            ride = b.ride
            if not ride:
                continue
            driver = ride.driver
            items.append(PassengerBookingSummaryItem(
                    booking_id=b.booking_id,
                    booking_status=b.status,
                    ride_id=ride.ride_id,
                    origin_name=ride.origin_name,
                    destination_name=ride.destination_name,
                    departure_time=ride.departure_time,
                    estimated_arrival_time=ride.estimated_arrival_time,
                    ride_status=ride.status.value if hasattr(ride.status, "value") else str(ride.status),
                    group_id=ride.group.group_id if ride.group else None,
                    group_name=ride.group.name if ride.group else None,
                    driver=DriverSummaryInfo(
                        full_name=driver.full_name or "נהג",
                        phone_number=getattr(driver, "phone_number", None),
                    ) if driver else None,
                ))
        return PassengerSummaryResponse(bookings=items)

    @staticmethod
    async def broadcast_driver_location(
        db: AsyncSession,
        booking_id: UUID,
        driver_id: UUID,
        body: DriverLocationReport,
    ) -> None:
        """Validate driver + active ride, then broadcast GPS to confirmed passengers."""
        booking = await BookingService.get_booking(db, booking_id)
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
        booking = await BookingService.get_booking(db, booking_id)
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
            return await crud_booking.get_booking_by_id_async(db, booking_id)
        except (BookingNotFoundError, ForbiddenRideActionError, RideNotAvailableError):
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error("cancel_booking failed booking_id=%s: %s", booking_id, e)
            raise

    @staticmethod
    async def get_user_bookings(
        db: AsyncSession,
        user_id: UUID,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ):
        """Paginated list of bookings for a user."""
        total = await crud_booking.get_user_bookings_count_async(db, user_id, status)
        offset = (page - 1) * limit
        bookings = await crud_booking.get_user_bookings_filtered_async(db, user_id, status, offset=offset, limit=limit)
        items = [BookingResponse.model_validate(b) for b in bookings]
        has_more = (page * limit) < total
        return PaginatedBookingsResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            has_more=has_more,
        )

    @staticmethod
    async def get_pending_requests(db: AsyncSession, ride_id: UUID, driver_id: UUID):
        """Pending join requests for a ride (driver only)."""
        ride = await db.get(Ride, ride_id)
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("גישה חסומה")
        return await crud_booking.get_ride_bookings_by_status_async(db, ride_id, BookingStatus.PENDING)

    @staticmethod
    async def get_active_bookings_for_driver(db: AsyncSession, driver_id: UUID):
        """In-progress bookings for active trip phases (driver)."""
        stmt = (
            select(Booking)
            .join(Ride)
            .where(
                Ride.driver_id == driver_id,
                Booking.status.in_(
                    [
                        BookingStatus.EN_ROUTE,
                        BookingStatus.ARRIVED,
                        BookingStatus.TRIP_IN_PROGRESS,
                    ],
                ),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_history_with_stats(db: AsyncSession, user_id: UUID, role: str):
        trips = await crud_booking.get_user_history(db, user_id=user_id, role=role)
        total_km = sum(float(t.ride.distance_km) for t in trips if t.ride and t.ride.distance_km)
        total_minutes = sum(float(t.ride.duration_min) for t in trips if t.ride and t.ride.duration_min)
        stats = {
            "count": len(trips),
            "total_km": round(total_km, 2),
            "total_hours": round(total_minutes / 60, 1),
        }
        return {"trips": trips, "stats": stats}

    @staticmethod
    async def get_notifications_for_user(db: AsyncSession, user_id: UUID) -> list[NotificationItemResponse]:
        """Unified notification feed: driver pending joins + passenger booking updates."""
        items: list[NotificationItemResponse] = []

        # As driver: pending join requests
        pending = await crud_booking.get_all_pending_bookings_for_driver(db, user_id)
        for b in pending:
            ride = b.ride
            other = None
            if b.passenger_request and b.passenger_request.user:
                other = getattr(b.passenger_request.user, "full_name", None) or "נוסע"
            items.append(
                NotificationItemResponse(
                    type="ride_request",
                    title="בקשה להצטרפות לנסיעה",
                    body=f"{other or 'נוסע'} מבקש להצטרף לנסיעה" if other else "בקשה להצטרפות",
                    action_url="/my-bookings?tab=driver",
                    created_at=b.created_at,
                    booking_id=b.booking_id,
                    ride_id=b.ride_id,
                    other_party_name=other,
                    ride_origin=getattr(ride, "origin_name", None),
                    ride_destination=getattr(ride, "destination_name", None),
                    status=BookingStatus.PENDING.value,
                ),
            )

        # As passenger: my bookings (approved / rejected / pending)
        my_bookings = await crud_booking.get_user_bookings_with_relations(db, user_id)
        for b in my_bookings:
            ride = b.ride
            driver_name = None
            if ride and getattr(ride, "driver", None):
                driver_name = getattr(ride.driver, "full_name", None) or "הנהג"
            status_val = getattr(b.status, "value", str(b.status)) if b.status else None
            if status_val == BookingStatus.CONFIRMED.value:
                ntype, title = "booking_confirmed", "אישור לנסיעה"
                body = f"{driver_name or 'הנהג'} אישר את בקשתך"
            elif status_val == BookingStatus.REJECTED.value:
                ntype, title = "booking_rejected", "דחיית בקשתך"
                body = f"{driver_name or 'הנהג'} דחה את בקשתך"
            else:
                ntype, title = "pending_approval", "בקשתך ממתינה"
                body = "בקשתך לנסיעה ממתינה לאישור הנהג"
            items.append(
                NotificationItemResponse(
                    type=ntype,
                    title=title,
                    body=body,
                    action_url="/my-bookings",
                    created_at=b.created_at,
                    booking_id=b.booking_id,
                    ride_id=b.ride_id,
                    other_party_name=driver_name,
                    ride_origin=getattr(ride, "origin_name", None) if ride else None,
                    ride_destination=getattr(ride, "destination_name", None) if ride else None,
                    status=status_val,
                ),
            )

        items.sort(key=lambda x: x.created_at, reverse=True)
        return items
