# app/domain/bookings/service.py
import logging
from urllib.parse import quote
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.booking import (
    RideNotAvailableError,
    BookingAlreadyExistsError,
    PassengerRequestNotFoundError,
    BookingNotFoundError,
    ForbiddenRideActionError,
    NoSeatsAvailableError,
)
from app.domain.bookings.crud import crud_booking

# ייבוא מה-Models וה-Enums
from app.domain.passengers.model import PassengerRequest
from app.domain.rides.model import Ride
from app.domain.bookings.model import Booking
from app.domain.bookings.enum import BookingStatus
from app.domain.rides.enum import RideStatus
from app.domain.bookings.schema import (
    BookingManifestItem,
    RideManifestResponse,
    NotificationItemResponse,
)

# אירועים – Outbox בלבד
from app.domain.events.outbox import publish_to_outbox
from app.domain.events.enum import DispatchTarget
from app.domain.notifications.constants import NotificationEvent
from sqlalchemy import select
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


class BookingService:
    @staticmethod
    async def request_to_join(
        db: AsyncSession,
        ride_id: UUID,
        request_id: UUID,
        num_seats: int = 1,
        current_user_id: Optional[UUID] = None,
    ) -> Booking:
        """בקשת הצטרפות לנסיעה. אירוע ל-Outbox – ה-Worker ישלח מייל לנהג."""
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
                        db, ride_id, p_req.passenger_id, request_id, num_seats
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
            print(
                f"[NOTIF] API: wrote to outbox booking_id={new_booking.booking_id}",
                flush=True,
            )
            logger.info(
                "[NOTIF] API: wrote to outbox event=booking.passenger_join_request booking_id=%s",
                new_booking.booking_id,
            )
            await db.commit()
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
        לוגיקה עסקית לביטול נסיעה שלמה על ידי נהג.
        חשוב: לא מפרסם Outbox. ה-caller אחראי על אירועים.
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
        """הפקת רשימת נוסעים עבור הנהג (כולל pending_approval + confirmed)."""
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

        manifest = []
        for b in bookings:
            user = b.passenger_request.user if b.passenger_request else None
            if not user:
                continue
            clean_phone = "".join(filter(str.isdigit, user.phone_number or ""))
            if clean_phone.startswith("0"):
                clean_phone = "972" + clean_phone[1:]
            manifest.append(
                {
                    "booking_id": b.booking_id,
                    "passenger_id": user.user_id,
                    "passenger_name": user.full_name,
                    "phone": user.phone_number or "",
                    "whatsapp_link": f"https://wa.me/{clean_phone}?text={quote('היי, אני הנהג שלך מהאפליקציה')}",
                    "num_seats": b.num_seats,
                    "status": b.status,
                    "reminder_sent": b.reminder_sent,
                    "pickup_name": b.pickup_name,
                    "pickup_time": b.pickup_time,
                    "destination_name": (b.passenger_request.destination_name if b.passenger_request else None),
                }
            )

        available_seats_left = max(0, ride.available_seats)
        return RideManifestResponse(
            ride_id=ride_id,
            total_confirmed_passengers=len(manifest),
            available_seats_left=available_seats_left,
            passengers=[BookingManifestItem(**item) for item in manifest],
        )

    @staticmethod
    async def cancel_all_bookings_for_request(db: AsyncSession, request_id: UUID) -> None:
        """ביטול כל ההזמנות של בקשה (לשימוש סינכרוני מ־PassengerService)."""
        stmt = select(Booking).where(Booking.request_id == request_id)
        result = await db.execute(stmt)
        bookings = list(result.scalars().all())
        for b in bookings:
            await crud_booking.execute_booking_cancellation(db, b)
        await db.commit()

    @staticmethod
    async def get_booking(db: AsyncSession, booking_id: UUID) -> Booking:
        """שליפת פרטי הזמנה בודדת"""
        booking = await crud_booking.get_booking_by_id_async(db, booking_id)
        if not booking:
            raise BookingNotFoundError(booking_id=str(booking_id))
        return booking

    @staticmethod
    async def approve_booking(db: AsyncSession, booking_id: UUID, driver_id: UUID) -> Booking:
        """אישור הזמנה על ידי נהג. מפרסם לאוטבוקס – הנוסע יקבל מייל ופוש."""
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
            return await crud_booking.get_booking_by_id_async(db, booking_id)
        except (
            BookingNotFoundError,
            ForbiddenRideActionError,
            RideNotAvailableError,
            NoSeatsAvailableError,
        ):
            await db.rollback()
            raise

    @staticmethod
    async def reject_booking(db: AsyncSession, booking_id: UUID, driver_id: UUID) -> Booking:
        """דחיית הזמנה על ידי נהג. מפרסם לאוטבוקס – הנוסע יקבל מייל ופוש."""
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
            return await crud_booking.get_booking_by_id_async(db, booking_id)
        except (BookingNotFoundError, ForbiddenRideActionError):
            await db.rollback()
            raise

    @staticmethod
    async def cancel_booking(db: AsyncSession, booking_id: UUID, current_user_id: UUID) -> Booking:
        """ביטול הזמנה (נוסע או נהג) – עם בדיקת הרשאות."""
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

    @staticmethod
    async def get_user_bookings(
        db: AsyncSession,
        user_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ):
        """שליפת הזמנות משתמש עם page-based pagination."""
        from app.domain.bookings.schema import PaginatedBookingsResponse, BookingResponse

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
        """שליפת בקשות הממתינות לאישור עבור נסיעה מסוימת"""
        ride = await db.get(Ride, ride_id)
        if not ride or ride.driver_id != driver_id:
            raise ForbiddenRideActionError("גישה חסומה")
        return await crud_booking.get_ride_bookings_by_status_async(db, ride_id, BookingStatus.PENDING)

    @staticmethod
    async def get_active_bookings_for_driver(db: AsyncSession, driver_id: UUID):
        """בוקינגים שבהם הנהג כרגע בביצוע מול נוסע."""
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
                    ]
                ),
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_history_with_stats(db: AsyncSession, user_id: UUID, role: str):
        trips = await crud_booking.get_user_history(db, user_id=user_id, role=role)
        total_km = sum(t.distance_km for t in trips if t.distance_km)
        total_minutes = sum(t.duration_minutes for t in trips if t.duration_minutes)
        stats = {
            "count": len(trips),
            "total_km": round(total_km, 2),
            "total_hours": round(total_minutes / 60, 1),
        }
        return {"trips": trips, "stats": stats}

    @staticmethod
    async def get_notifications_for_user(db: AsyncSession, user_id: UUID) -> List[NotificationItemResponse]:
        """אוסף כל ההתראות למשתמש: כנהג – בקשות להצטרפות; כנוסע – אישור/דחייה/ממתין."""
        items: List[NotificationItemResponse] = []

        # כנהג: בקשות ממתינות
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
                )
            )

        # כנוסע: ההזמנות שלי (אישור / דחייה / ממתין)
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
                )
            )

        items.sort(key=lambda x: x.created_at, reverse=True)
        return items
