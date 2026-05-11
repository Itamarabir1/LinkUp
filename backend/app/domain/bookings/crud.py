from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, with_loader_criteria

from app.core.exceptions.booking import ForbiddenRideActionError, NoSeatsAvailableError
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.passengers.enum import PassengerStatus
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride

_BOOKINGS_SUMMARY_ACTIVE_SOFT_LIMIT = 200

_DRIVER_ACTIVE_BOOKING_STATUSES = (
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.EN_ROUTE,
    BookingStatus.ARRIVED,
    BookingStatus.TRIP_IN_PROGRESS,
)

_PASSENGER_ACTIVE_BOOKING_STATUSES = _DRIVER_ACTIVE_BOOKING_STATUSES

# Statuses where the booking has actually consumed seats on the ride
# (PENDING does not — seats are decremented only at approval).
_SEAT_RESERVING_BOOKING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.EN_ROUTE,
    BookingStatus.ARRIVED,
    BookingStatus.TRIP_IN_PROGRESS,
)

_DRIVER_HISTORY_BOOKING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.CANCELLED,
    BookingStatus.COMPLETED,
    BookingStatus.REJECTED,
)


def _status_from_bookings_list(bookings: list[Booking]) -> PassengerStatus:
    """Derive PassengerRequest status from bookings (single source of truth; no DB)."""
    if not bookings:
        return PassengerStatus.ACTIVE

    has_confirmed = any(b.status == BookingStatus.CONFIRMED for b in bookings)
    if has_confirmed:
        all_completed = all(b.status == BookingStatus.COMPLETED for b in bookings)
        if all_completed:
            return PassengerStatus.COMPLETED
        return PassengerStatus.APPROVED

    has_pending = any(b.status == BookingStatus.PENDING for b in bookings)
    if has_pending:
        return PassengerStatus.PENDING

    all_rejected = all(b.status == BookingStatus.REJECTED for b in bookings)
    if all_rejected:
        return PassengerStatus.REJECTED

    return PassengerStatus.ACTIVE


class CRUDBooking:
    """
    Database access layer for Booking entities.
    Centralizes read/write helpers used by the domain.
    """

    # --- Queries ---

    async def get_booking_by_id_async(self, db: AsyncSession, booking_id: UUID) -> Booking | None:
        """Async variant of get_booking_by_id."""
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
        id: UUID | None = None,
        booking_id: UUID | None = None,
    ) -> Booking | None:
        """Async fetch for a booking (notifications). Accepts id= or booking_id=."""
        bid = id or booking_id
        if bid is None:
            return None
        return await self.get_booking_by_id_async(db, bid)

    async def get_async(self, db: AsyncSession, booking_id: UUID) -> Booking | None:
        """Async fetch for a booking with relationships loaded (for API endpoints)."""
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

    async def get_ride_for_update(self, db: AsyncSession, ride_id: UUID) -> Ride | None:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Ride).where(Ride.ride_id == rid).with_for_update()
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_existing_booking_async(self, db: AsyncSession, ride_id: UUID, request_id: UUID) -> Booking | None:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        stmt = select(Booking).where(
            Booking.ride_id == rid,
            Booking.request_id == reqid,
            Booking.status != BookingStatus.CANCELLED,
        )
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_booking_by_ride_and_passenger_async(self, db: AsyncSession, ride_id: UUID, passenger_id: UUID) -> Booking | None:
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
    ) -> Booking | None:
        """Reuses an existing booking (CANCELLED/REJECTED) for a new request — allows re-request without breaking unique_passenger_per_ride."""
        existing = await self.get_booking_by_ride_and_passenger_async(db, ride_id, passenger_id)
        if not existing or existing.status not in (
            BookingStatus.CANCELLED,
            BookingStatus.REJECTED,
        ):
            return None
        existing.request_id = request_id
        existing.num_seats = num_seats
        existing.status = BookingStatus.PENDING
        # Copy pickup stop details from PassengerRequest
        p_req = await db.get(PassengerRequest, request_id)
        if p_req:
            p_req.status = PassengerStatus.MATCHED
            existing.pickup_name = p_req.pickup_name
            existing.pickup_point = p_req.pickup_geom
            existing.pickup_time = p_req.requested_departure_time
        await db.flush()
        return existing

    # --- Writes ---

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

        # Re-check seat availability — time may have passed since request;
        # last seat might have been taken by another passenger
        if ride.available_seats < booking.num_seats:
            raise NoSeatsAvailableError("אין מקומות פנויים לאישור הזמנה זו")
        ride.available_seats -= booking.num_seats
        if ride.available_seats <= 0:
            ride.status = RideStatus.FULL

        # Recompute PassengerRequest status from all bookings
        if booking.request_id:
            await self.update_passenger_request_status_from_bookings(db, booking.request_id)

    async def execute_booking_rejection(self, db: AsyncSession, booking: Booking):
        booking.status = BookingStatus.REJECTED

        # Recompute PassengerRequest status from all bookings
        if booking.request_id:
            await self.update_passenger_request_status_from_bookings(db, booking.request_id)

    async def execute_booking_cancellation(self, db: AsyncSession, booking: Booking):
        if booking.status == BookingStatus.CONFIRMED:
            ride = booking.ride
            ride.available_seats += booking.num_seats
            if ride.status != RideStatus.CANCELLED:
                ride.status = RideStatus.OPEN

        booking.status = BookingStatus.CANCELLED

        # Recompute PassengerRequest status from all bookings
        if booking.request_id:
            await self.update_passenger_request_status_from_bookings(db, booking.request_id)

    async def bulk_cancel_bookings_for_request(self, db: AsyncSession, request_id: UUID) -> int:
        """
        Cancel all non-cancelled bookings for a passenger request in bulk.

        Replaces the legacy O(N²) loop:
        - Aggregates seats to restore per ride (status in CONFIRMED/EN_ROUTE/ARRIVED/TRIP_IN_PROGRESS).
        - Locks affected rides FOR UPDATE (race-safe vs. approve_booking).
        - Restores seats and resets ride.status to OPEN, preserving CANCELLED.
        - Bulk-updates booking rows to CANCELLED in a single statement.

        Caller is responsible for committing and for setting PassengerRequest.status.
        Returns number of bookings cancelled.
        """
        if request_id is None:
            return 0
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id

        seats_stmt = (
            select(Booking.ride_id, func.sum(Booking.num_seats).label("delta"))
            .where(
                Booking.request_id == reqid,
                Booking.status.in_(_SEAT_RESERVING_BOOKING_STATUSES),
            )
            .group_by(Booking.ride_id)
        )
        rows = (await db.execute(seats_stmt)).all()

        if rows:
            ride_ids = [r.ride_id for r in rows]
            await db.execute(
                select(Ride.ride_id).where(Ride.ride_id.in_(ride_ids)).with_for_update(),
            )
            for ride_id, delta in rows:
                await db.execute(
                    text(
                        "UPDATE rides "
                        "SET available_seats = available_seats + :delta, "
                        "    status = CASE WHEN status = CAST(:cancelled AS ride_status) "
                        "                 THEN status "
                        "                 ELSE CAST(:open AS ride_status) END, "
                        "    updated_at = now() "
                        "WHERE ride_id = :rid",
                    ),
                    {
                        "delta": int(delta),
                        "cancelled": RideStatus.CANCELLED.value,
                        "open": RideStatus.OPEN.value,
                        "rid": ride_id,
                    },
                )

        res = await db.execute(
            sa_update(Booking)
            .where(Booking.request_id == reqid, Booking.status != BookingStatus.CANCELLED)
            .values(status=BookingStatus.CANCELLED.value),
        )
        return int(res.rowcount or 0)

    async def cancel_all_bookings_for_ride(self, db: AsyncSession, ride_id: UUID):
        """
        Broad ride cancellation:
        1. Cancels all bookings for the ride.
        2. Sets linked passenger requests (PassengerRequests) to ACTIVE.
        """
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Booking.request_id).where(Booking.ride_id == rid, Booking.request_id.isnot(None))
        result = await db.execute(stmt)
        request_ids = [r[0] for r in result.all()]
        if request_ids:
            await db.execute(
                sa_update(PassengerRequest).where(PassengerRequest.request_id.in_(request_ids)).values(status=PassengerStatus.ACTIVE.value),
            )
        await db.execute(sa_update(Booking).where(Booking.ride_id == rid).values(status=BookingStatus.CANCELLED.value))
        await db.execute(
            text("UPDATE rides SET status = CAST(:status AS ride_status), updated_at = now() WHERE ride_id = :ride_id"),
            {"status": RideStatus.CANCELLED.value, "ride_id": rid},
        )
        await db.flush()

    # --- Helpers used by BookingService ---

    async def get_user_bookings_count_async(self, db: AsyncSession, user_id: UUID, status_filter: str | None = None) -> int:
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
        status_filter: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Booking]:
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

    async def get_user_bookings_with_relations(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Booking]:
        """Passenger bookings with ride and driver loaded (notifications UI), keyset paginated."""
        uid = UUID(str(user_id)) if isinstance(user_id, str) else user_id
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .where(Booking.passenger_id == uid)
            .order_by(Booking.created_at.desc(), Booking.booking_id.desc())
            .limit(limit + 1)
        )
        if after is not None:
            ct, bid = after
            stmt = stmt.where(or_(Booking.created_at < ct, and_(Booking.created_at == ct, Booking.booking_id < bid)))
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_ride_bookings_by_status_async(self, db: AsyncSession, ride_id: UUID, booking_status: str) -> list[Booking]:
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Booking).where(Booking.ride_id == rid, Booking.status == booking_status)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_ride_bookings_by_status_with_relations(self, db: AsyncSession, ride_id: UUID, booking_status: str) -> list[Booking]:
        """Same filter as get_ride_bookings_by_status_async but with passenger relationships loaded."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = (
            select(Booking)
            .options(
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Booking.passenger),
            )
            .where(Booking.ride_id == rid, Booking.status == booking_status)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_all_pending_bookings_for_driver(
        self,
        db: AsyncSession,
        driver_id: UUID,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Booking]:
        """All pending approval requests for the driver’s rides (notifications UI)."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        stmt = (
            select(Booking)
            .join(Ride)
            .where(Ride.driver_id == did, Booking.status == BookingStatus.PENDING)
            .options(
                joinedload(Booking.ride),
                joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
            )
            .order_by(Booking.created_at.desc(), Booking.booking_id.desc())
            .limit(limit + 1)
        )
        if after is not None:
            ct, bid = after
            stmt = stmt.where(or_(Booking.created_at < ct, and_(Booking.created_at == ct, Booking.booking_id < bid)))
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

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
        Driver cancels a ride (full async logic).
        - Enforces permissions (ride driver only)
        - Sets all bookings on the ride to CANCELLED
        - Recomputes PassengerRequest status for each request_id on the ride
        - Sets the ride itself to cancelled

        Note: no commit here; caller owns commit/rollback.
        """
        stmt = select(Ride).where(Ride.ride_id == ride_id).with_for_update()
        result = await db.execute(stmt)
        ride = result.scalars().first()
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("אינך מורשה לבטל נסיעה זו")

        req_ids = await self.get_request_ids_for_ride(db, ride_id)

        await self.bulk_update_bookings_status(db, ride_id, BookingStatus.CANCELLED)

        # After cancelling ride bookings, recompute PassengerRequest status in bulk
        # (same request may have bookings on other rides)
        unique_req_ids = sorted({r for r in req_ids if r is not None})
        if unique_req_ids:
            res = await db.execute(select(Booking).where(Booking.request_id.in_(unique_req_ids)))
            by_req: dict[UUID, list[Booking]] = defaultdict(list)
            for b in res.scalars().all():
                if b.request_id is not None:
                    by_req[b.request_id].append(b)
            by_status: dict[PassengerStatus, list[UUID]] = defaultdict(list)
            for req_uid in unique_req_ids:
                by_status[_status_from_bookings_list(by_req.get(req_uid, []))].append(req_uid)
            for st, ids in by_status.items():
                await self.bulk_update_requests_status(db, ids, st)

        ride.status = RideStatus.CANCELLED
        await db.flush()
        return req_ids

    async def bulk_update_requests_status(self, db: AsyncSession, request_ids: list, new_status: PassengerStatus):
        status_value = new_status.value if hasattr(new_status, "value") else str(new_status)
        await db.execute(sa_update(PassengerRequest).where(PassengerRequest.request_id.in_(request_ids)).values(status=status_value))

    async def determine_passenger_request_status(self, db: AsyncSession, request_id: UUID) -> PassengerStatus:
        """
        Derives the appropriate PassengerRequest status from its bookings.
        """
        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        result = await db.execute(select(Booking).where(Booking.request_id == reqid))
        bookings = list(result.scalars().all())
        return _status_from_bookings_list(bookings)

    async def update_passenger_request_status_from_bookings(self, db: AsyncSession, request_id: UUID) -> None:
        """Updates PassengerRequest status based on its bookings."""
        if not request_id:
            return

        reqid = UUID(str(request_id)) if isinstance(request_id, str) else request_id
        new_status = await self.determine_passenger_request_status(db, reqid)
        # Pass enum .value, not the enum instance
        status_value = new_status.value if hasattr(new_status, "value") else str(new_status)
        await db.execute(sa_update(PassengerRequest).where(PassengerRequest.request_id == reqid).values(status=status_value))

    async def complete_bookings_by_ride_ids(self, db: AsyncSession, ride_ids: list):
        """Updates status for all bookings belonging to the given ride ids."""
        await db.execute(
            sa_update(Booking)
            .where(
                Booking.ride_id.in_(ride_ids),
                Booking.status == BookingStatus.CONFIRMED,
            )
            .values(status=BookingStatus.COMPLETED.value),
        )

    async def get_driver_active_rides(self, db: AsyncSession, driver_id: UUID) -> list[Ride]:
        """OPEN/FULL/ACTIVE rides with in-flight bookings loaded (cap 200)."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        stmt = (
            select(Ride)
            .where(
                Ride.driver_id == did,
                Ride.status.in_([RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE]),
            )
            .options(
                joinedload(Ride.bookings).joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Ride.group),
                with_loader_criteria(Booking, Booking.status.in_(list(_DRIVER_ACTIVE_BOOKING_STATUSES))),
            )
            .order_by(Ride.departure_time.asc())
            .limit(_BOOKINGS_SUMMARY_ACTIVE_SOFT_LIMIT)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_driver_history_rides(
        self,
        db: AsyncSession,
        driver_id: UUID,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Ride]:
        """Completed/cancelled rides; bookings loaded for manifest (history statuses). ORDER BY departure_time DESC."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        stmt = (
            select(Ride)
            .where(
                Ride.driver_id == did,
                Ride.status.in_([RideStatus.COMPLETED, RideStatus.CANCELLED]),
            )
            .options(
                joinedload(Ride.bookings).joinedload(Booking.passenger_request).joinedload(PassengerRequest.user),
                joinedload(Ride.group),
                with_loader_criteria(Booking, Booking.status.in_(list(_DRIVER_HISTORY_BOOKING_STATUSES))),
            )
            .order_by(Ride.departure_time.desc(), Ride.ride_id.desc())
            .limit(limit + 1)
        )
        if after is not None:
            ct, cid = after
            stmt = stmt.where(or_(Ride.departure_time < ct, and_(Ride.departure_time == ct, Ride.ride_id < cid)))
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_passenger_active_bookings(self, db: AsyncSession, passenger_id: UUID) -> list[Booking]:
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        stmt = (
            select(Booking)
            .join(Booking.ride)
            .where(
                Booking.passenger_id == pid,
                Booking.status.in_(list(_PASSENGER_ACTIVE_BOOKING_STATUSES)),
            )
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.ride).joinedload(Ride.group),
            )
            .order_by(Ride.departure_time.asc())
            .limit(_BOOKINGS_SUMMARY_ACTIVE_SOFT_LIMIT)
        )
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_passenger_history_bookings(
        self,
        db: AsyncSession,
        passenger_id: UUID,
        limit: int,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Booking]:
        pid = UUID(str(passenger_id)) if isinstance(passenger_id, str) else passenger_id
        stmt = (
            select(Booking)
            .join(Ride)
            .where(
                Booking.passenger_id == pid,
                Booking.status.in_([BookingStatus.COMPLETED, BookingStatus.CANCELLED, BookingStatus.REJECTED]),
            )
            .options(
                joinedload(Booking.ride).joinedload(Ride.driver),
                joinedload(Booking.ride).joinedload(Ride.group),
            )
            .order_by(Ride.departure_time.desc(), Booking.booking_id.desc())
            .limit(limit + 1)
        )
        if after is not None:
            ct, bid = after
            stmt = stmt.where(or_(Ride.departure_time < ct, and_(Ride.departure_time == ct, Booking.booking_id < bid)))
        result = await db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_user_history(self, db: AsyncSession, user_id: UUID, role: str) -> list[Booking]:
        # joinedload avoids N+1 queries
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
