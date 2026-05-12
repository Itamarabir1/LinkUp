# app/domain/bookings/booking_reads_service.py
"""Read-only aggregations: manifests, summaries, history, notifications."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions.booking import ForbiddenRideActionError
from app.core.exceptions.validation import BadRequestError
from app.core.constants import (
    MANIFEST_BOOKING_ROW_LIMIT,
    NOTIFICATIONS_DEFAULT_LIMIT,
    NOTIFICATIONS_MAX_LIMIT,
)
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.manifest_mapping import booking_to_manifest_item
from app.domain.bookings.model import Booking
from app.domain.bookings.schema import (
    BookingManifestItem,
    BookingResponse,
    DriverActiveResponse,
    DriverHistoryResponse,
    DriverSummaryInfo,
    NotificationItemResponse,
    NotificationReadItem,
    PaginatedNotificationsResponse,
    PaginatedBookingsResponse,
    PassengerActiveResponse,
    PassengerBookingSummaryItem,
    PassengerHistoryResponse,
    RideManifestResponse,
    RideWithPassengersItem,
)
from app.core.pagination.cursor import CursorDecodeError, decode_cursor, encode_cursor
from app.domain.notifications.model import NotificationRead
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
    def _ride_to_with_passengers_item(ride: Ride) -> RideWithPassengersItem:
        passengers = []
        for b in ride.bookings:
            row = booking_to_manifest_item(b)
            if row:
                passengers.append(row)
        return RideWithPassengersItem(
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

    @staticmethod
    def _booking_to_passenger_summary_item(booking: Booking) -> PassengerBookingSummaryItem | None:
        ride = booking.ride
        if not ride:
            return None
        driver = ride.driver
        return PassengerBookingSummaryItem(
            booking_id=booking.booking_id,
            booking_status=booking.status,
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

    @staticmethod
    async def get_ride_manifest(db: AsyncSession, ride_id: UUID, driver_id: UUID) -> RideManifestResponse:
        """Driver manifest: pending + confirmed bookings with contact hints."""
        ride = await db.get(Ride, ride_id)
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("גישה חסומה")

        status_where = Booking.status.in_([BookingStatus.PENDING.value, BookingStatus.CONFIRMED.value])
        agg_stmt = (
            select(
                func.coalesce(
                    func.sum(case((Booking.status == BookingStatus.CONFIRMED.value, 1), else_=0)),
                    0,
                ),
                func.coalesce(
                    func.sum(case((Booking.status == BookingStatus.PENDING.value, 1), else_=0)),
                    0,
                ),
            )
            .select_from(Booking)
            .where(Booking.ride_id == ride_id, status_where)
        )
        agg_row = (await db.execute(agg_stmt)).one()
        confirmed_total = int(agg_row[0])
        pending_total = int(agg_row[1])

        status_rank = case(
            (Booking.status == BookingStatus.CONFIRMED.value, 0),
            (Booking.status == BookingStatus.PENDING.value, 1),
            else_=9,
        )
        stmt_list = (
            select(Booking)
            .options(joinedload(Booking.passenger_request).joinedload(PassengerRequest.user))
            .where(Booking.ride_id == ride_id, status_where)
            .order_by(status_rank.asc(), Booking.created_at.desc())
            .limit(MANIFEST_BOOKING_ROW_LIMIT)
        )
        bookings = list((await db.execute(stmt_list)).scalars().all())

        manifest_items: list[BookingManifestItem] = []
        for b in bookings:
            item = booking_to_manifest_item(b)
            if item:
                manifest_items.append(item)

        available_seats_left = max(0, ride.available_seats)
        combined = confirmed_total + pending_total
        manifest_truncated = combined > MANIFEST_BOOKING_ROW_LIMIT
        return RideManifestResponse(
            ride_id=ride_id,
            confirmed_total=confirmed_total,
            pending_total=pending_total,
            manifest_truncated=manifest_truncated,
            total_confirmed_passengers=confirmed_total,
            available_seats_left=available_seats_left,
            passengers=manifest_items,
        )

    @staticmethod
    async def get_driver_active_summary(db: AsyncSession, driver_id: UUID) -> DriverActiveResponse:
        """Active rides snapshot (soft cap 200), not a complete active feed for heavy users."""
        rides = await crud_booking.get_driver_active_rides(db, driver_id)
        return DriverActiveResponse(
            rides=[BookingReadsService._ride_to_with_passengers_item(r) for r in rides],
        )

    @staticmethod
    async def get_driver_history_summary(
        db: AsyncSession,
        driver_id: UUID,
        limit: int = 20,
        after: str | None = None,
    ) -> DriverHistoryResponse:
        cursor_tuple = None
        if after:
            try:
                cursor_tuple = decode_cursor(after)
            except CursorDecodeError as e:
                raise BadRequestError("מסמן עמוד לא תקין") from e

        rides = await crud_booking.get_driver_history_rides(db, driver_id, limit, after=cursor_tuple)
        has_more = len(rides) > limit
        page = rides[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.departure_time, last.ride_id)
        return DriverHistoryResponse(
            rides=[BookingReadsService._ride_to_with_passengers_item(r) for r in page],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    async def get_passenger_active_summary(db: AsyncSession, passenger_id: UUID) -> PassengerActiveResponse:
        """Active bookings snapshot (soft cap 200), not a complete active feed for heavy users."""
        bookings = await crud_booking.get_passenger_active_bookings(db, passenger_id)
        items: list[PassengerBookingSummaryItem] = []
        for b in bookings:
            row = BookingReadsService._booking_to_passenger_summary_item(b)
            if row:
                items.append(row)
        return PassengerActiveResponse(bookings=items)

    @staticmethod
    async def get_passenger_history_summary(
        db: AsyncSession,
        passenger_id: UUID,
        limit: int = 20,
        after: str | None = None,
    ) -> PassengerHistoryResponse:
        cursor_tuple = None
        if after:
            try:
                cursor_tuple = decode_cursor(after)
            except CursorDecodeError as e:
                raise BadRequestError("מסמן עמוד לא תקין") from e

        bookings = await crud_booking.get_passenger_history_bookings(db, passenger_id, limit, after=cursor_tuple)
        has_more = len(bookings) > limit
        page = bookings[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            ride = last.ride
            if ride is not None:
                next_cursor = encode_cursor(ride.departure_time, last.booking_id)
        items: list[PassengerBookingSummaryItem] = []
        for b in page:
            row = BookingReadsService._booking_to_passenger_summary_item(b)
            if row:
                items.append(row)
        return PassengerHistoryResponse(
            bookings=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    async def get_user_bookings(
        db: AsyncSession,
        user_id: UUID,
        status: str | None = None,
        limit: int = 20,
        after: str | None = None,
    ) -> PaginatedBookingsResponse:
        """Cursor-paginated list of bookings for a user."""
        cursor_tuple = None
        if after:
            try:
                cursor_tuple = decode_cursor(after)
            except CursorDecodeError as e:
                raise BadRequestError("מסמן עמוד לא תקין") from e

        bookings = await crud_booking.get_user_bookings_filtered_async(db, user_id, status, limit=limit, after=cursor_tuple)
        has_more = len(bookings) > limit
        page = bookings[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.booking_id)
        items = [BookingResponse.model_validate(b) for b in page]
        return PaginatedBookingsResponse(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit,
        )

    @staticmethod
    async def get_pending_requests(db: AsyncSession, ride_id: UUID, driver_id: UUID):
        """Pending join requests for a ride (driver only)."""
        ride = await db.get(Ride, ride_id)
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("גישה חסומה")
        return await crud_booking.get_ride_bookings_by_status_with_relations(db, ride_id, BookingStatus.PENDING)

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
    def _driver_pending_to_notification(b: Booking) -> NotificationItemResponse:
        ride = b.ride
        other = None
        if b.passenger_request and b.passenger_request.user:
            other = getattr(b.passenger_request.user, "full_name", None) or "נוסע"
        return NotificationItemResponse(
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
        )

    @staticmethod
    def _passenger_booking_to_notification(b: Booking) -> NotificationItemResponse:
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
        return NotificationItemResponse(
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
        )

    @staticmethod
    async def get_notifications_for_user(
        db: AsyncSession,
        user_id: UUID,
        *,
        limit: int = NOTIFICATIONS_DEFAULT_LIMIT,
        after: str | None = None,
    ) -> PaginatedNotificationsResponse:
        """Unified cursor-paginated feed: driver pending joins + passenger booking updates."""
        lim = max(1, min(limit, NOTIFICATIONS_MAX_LIMIT))
        cursor_tuple = None
        if after:
            try:
                cursor_tuple = decode_cursor(after)
            except CursorDecodeError as e:
                raise BadRequestError("מסמן עמוד לא תקין") from e

        pending = await crud_booking.get_all_pending_bookings_for_driver(
            db,
            user_id,
            limit=lim,
            after=cursor_tuple,
        )
        my_bookings = await crud_booking.get_user_bookings_with_relations(
            db,
            user_id,
            limit=lim,
            after=cursor_tuple,
        )

        items: list[NotificationItemResponse] = [
            *(BookingReadsService._driver_pending_to_notification(b) for b in pending),
            *(BookingReadsService._passenger_booking_to_notification(b) for b in my_bookings),
        ]
        items.sort(key=lambda x: (x.created_at, x.booking_id), reverse=True)

        has_more = len(items) > lim
        page = items[:lim]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.booking_id)

        read_keys = await BookingReadsService._get_read_keys(db, user_id, page)
        unread = 0
        for item in page:
            key = (item.booking_id, item.created_at)
            item.is_read = key in read_keys
            if not item.is_read:
                unread += 1

        return PaginatedNotificationsResponse(
            items=page,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=lim,
            unread_count=unread,
        )

    @staticmethod
    async def _get_read_keys(
        db: AsyncSession,
        user_id: UUID,
        items: list[NotificationItemResponse],
    ) -> set[tuple[UUID, datetime]]:
        """Batch-fetch read state for a page of notification items."""
        if not items:
            return set()
        pairs = [(item.booking_id, item.created_at) for item in items]
        booking_ids = list({p[0] for p in pairs})
        stmt = select(NotificationRead.booking_id, NotificationRead.created_at).where(
            NotificationRead.user_id == user_id,
            NotificationRead.booking_id.in_(booking_ids),
        )
        rows = (await db.execute(stmt)).all()
        return {(row[0], row[1]) for row in rows}

    @staticmethod
    async def mark_notifications_read(
        db: AsyncSession,
        user_id: UUID,
        items: list[NotificationReadItem],
    ) -> None:
        """Upsert notification read-state rows (idempotent)."""
        values = [{"user_id": user_id, "booking_id": it.booking_id, "created_at": it.created_at} for it in items]
        stmt = pg_insert(NotificationRead).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "booking_id", "created_at"])
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def mark_all_notifications_read(db: AsyncSession, user_id: UUID) -> None:
        """Mark every current notification as read in one pass."""
        all_items_resp = await BookingReadsService.get_notifications_for_user(db, user_id, limit=NOTIFICATIONS_MAX_LIMIT)
        if not all_items_resp.items:
            return
        values = [{"user_id": user_id, "booking_id": item.booking_id, "created_at": item.created_at} for item in all_items_resp.items]
        stmt = pg_insert(NotificationRead).values(values)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "booking_id", "created_at"])
        await db.execute(stmt)
        await db.commit()
