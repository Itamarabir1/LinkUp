# app/domain/bookings/booking_reads_service.py
"""Read-only aggregations: manifests, summaries, history, notifications."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions.booking import ForbiddenRideActionError
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.manifest_mapping import booking_to_manifest_item
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
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.model import Ride
from app.domain.users.model import User


class BookingReadsService:
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
            item = booking_to_manifest_item(b)
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
        rides = await crud_booking.get_driver_rides_with_passengers(db, driver_id)
        items = []
        for ride in rides:
            passengers = []
            for b in ride.bookings:
                row = booking_to_manifest_item(b)
                if row:
                    passengers.append(row)
            items.append(
                RideWithPassengersItem(
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
                )
            )
        return DriverSummaryResponse(rides=items)

    @staticmethod
    async def get_passenger_summary(db: AsyncSession, passenger_id: UUID) -> PassengerSummaryResponse:
        """All passenger bookings with ride + driver info — single DB round-trip."""
        bookings = await crud_booking.get_passenger_bookings_with_rides(db, passenger_id)
        items = []
        for b in bookings:
            ride = b.ride
            if not ride:
                continue
            driver = ride.driver
            items.append(
                PassengerBookingSummaryItem(
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
                    driver=BookingReadsService._driver_to_summary(driver),
                )
            )
        return PassengerSummaryResponse(bookings=items)

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
