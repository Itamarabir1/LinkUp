import json
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import LinkupError
from app.core.exceptions.infrastructure import RouteNotFoundError
from app.core.exceptions.ride import (
    InvalidRideStatusError,
    NoConfirmedBookingsError,
    RideAlreadyCancelledError,
    RideNotFoundError,
    SessionExpiredError,
)
from app.core.exceptions.validation import SameOriginDestinationError
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.enum import BookingStatus
from app.domain.events.enum import DispatchTarget
from app.domain.events.outbox import publish_to_outbox
from app.domain.geo import processor as geo_proc
from app.domain.notifications.constants import NotificationEvent
from app.domain.rides.crud import crud_ride
from app.domain.rides.enum import RideBroadcastAction, RideStatus
from app.domain.rides.mapper import RideMapper
from app.domain.rides.model import Ride
from app.domain.rides.repository import RideCacheRepository, ride_cache_repo
from app.domain.rides.schema import (
    RideCreate,
    RidePreviewCreate,
    RidePreviewResponse,
    RideResponse,
    RideUpdate,
)
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.keys import RIDES_LIST_CHANNEL
from app.infrastructure.redis.publisher import publish_ride_event

logger = structlog.get_logger(__name__)


class _RideNotificationFactory:
    _CONFIG = {
        RideBroadcastAction.CREATED.value: {
            "color": "green",
            "message": "נסיעה חדשה זמינה כעת!",
            "event_prefix": "RIDE_CREATED",
        },
        RideBroadcastAction.UPDATED.value: {
            "color": "orange",
            "message": "עדכון בנסיעה (למשל מקום תפוס)",
            "event_prefix": "RIDE_UPDATED",
        },
        RideStatus.CANCELLED.value: {
            "color": "red",
            "message": "הנסיעה בוטלה על ידי הנהג",
            "event_prefix": "RIDE_CANCELLED",
        },
        RideStatus.COMPLETED.value: {
            "color": "green",
            "message": "הנסיעה הסתיימה בהצלחה",
            "event_prefix": "RIDE_COMPLETED",
        },
    }

    @classmethod
    def create_broadcast_payload(cls, ride, action: str) -> dict[str, Any]:
        config = cls._CONFIG.get(
            action,
            {
                "color": "gray",
                "message": "עדכון בנסיעה",
                "event_prefix": "RIDE_UPDATED",
            },
        )
        return {
            "event": config["event_prefix"],
            "ride_id": str(ride.ride_id),
            "status": ride.status.value if hasattr(ride.status, "value") else str(ride.status),
            "color": config["color"],
            "message": f"{config['message']} (מ-{ride.origin_name} ל-{ride.destination_name})",
        }


class RideService:
    def __init__(self, cache_repo: RideCacheRepository = ride_cache_repo):
        self.cache = cache_repo

    # --- Preview ---

    async def get_ride_preview(self, preview_in: RidePreviewCreate) -> RidePreviewResponse:
        """שלב 1: יצירת תצוגה מקדימה של מסלולים אפשריים ושמירתם ב-Cache."""
        self._validate_preview_input(preview_in)
        origin_address = await geo_proc.resolve_origin_address(
            preview_in.origin_name,
            preview_in.origin_lat,
            preview_in.origin_lon,
        )
        geo_data = await geo_proc.get_full_routing_data(
            origin_address,
            preview_in.destination_name,
            preview_in.departure_time,
        )
        if not geo_data:
            raise RouteNotFoundError(origin=origin_address, destination=preview_in.destination_name)
        preview_res = RidePreviewResponse.from_processor(
            geo_data=geo_data,
            preview_in=preview_in,
            origin_address=origin_address,
        )
        await self.cache.save_preview(preview_res, preview_in)
        return preview_res

    @staticmethod
    def _validate_preview_input(preview_in: RidePreviewCreate) -> None:
        if preview_in.origin_name and preview_in.origin_name == preview_in.destination_name:
            raise SameOriginDestinationError(location_name=preview_in.origin_name)

    # --- Create ride ---

    async def create_ride(self, db: AsyncSession, ride_in: RideCreate, current_user_id: UUID) -> RideResponse:
        """שלב 2: אישור סופי של הנסיעה והעברתה מה-Cache ל-PostgreSQL."""
        cached_data = await self._validate_and_get_cached_ride(ride_in)
        cached_data["driver_id"] = current_user_id
        if ride_in.group_id:
            cached_data["group_id"] = ride_in.group_id
        new_ride = RideMapper.map_cache_to_model(
            cached_data=cached_data,
            selected_index=ride_in.selected_route_index,
        )

        try:
            await self._persist_ride_and_publish_event(db, new_ride)
            response = self._build_ride_response(new_ride, cached_data, ride_in)
            await self._after_ride_created(response, new_ride, ride_in.session_id)
            return response
        except Exception as e:
            await db.rollback()
            logger.error("Failed to save ride to DB: %s", e)
            raise

    async def _validate_and_get_cached_ride(self, ride_in: RideCreate) -> dict[str, Any]:
        if not (ride_in.session_id and str(ride_in.session_id).strip()):
            logger.warning("create_ride_empty_session_id")
            raise SessionExpiredError(session_id=ride_in.session_id or "")
        cached_data = await self.cache.get_preview(ride_in.session_id)
        if not cached_data:
            logger.warning("create_ride: no preview in cache for session_id=%s", ride_in.session_id)
            raise SessionExpiredError(session_id=ride_in.session_id)
        return cached_data

    @staticmethod
    async def _persist_ride_and_publish_event(db: AsyncSession, new_ride: Ride) -> None:
        db.add(new_ride)
        await db.flush()
        await publish_to_outbox(db, "ride.created", {"ride_id": str(new_ride.ride_id)})
        await db.commit()
        await db.refresh(new_ride)

    @staticmethod
    def _build_ride_response(new_ride: Ride, cached_data: dict[str, Any], ride_in: RideCreate) -> RideResponse:
        response = RideMapper.to_response(new_ride)
        if not response.route_coords and cached_data.get("routes"):
            selected_route = cached_data["routes"][ride_in.selected_route_index]
            response = response.model_copy(update={"route_coords": selected_route.get("coords", [])})
        return response

    async def _after_ride_created(self, response: RideResponse, new_ride: Ride, session_id: str) -> None:
        await self.cache.delete_preview(session_id)
        try:
            payload = _RideNotificationFactory.create_broadcast_payload(new_ride, RideBroadcastAction.CREATED.value)
            payload["ride"] = response.model_dump(mode="json")
            await broadcast.publish(RIDES_LIST_CHANNEL, json.dumps(payload))
        except Exception as e:
            logger.warning("Broadcast ride created failed (ride still saved): %s", e)

    # --- Read ---

    @staticmethod
    async def get_ride_by_id(db: AsyncSession, ride_id: UUID):
        """שליפת נסיעה לפי מזהה (לשימוש ב-API עם AsyncSession)."""
        return await crud_ride.get_async(db, ride_id)

    async def get_my_rides(
        self,
        db: AsyncSession,
        driver_id: UUID,
        status: str | None = None,
    ) -> list[RideResponse]:
        """רשימת נסיעות של הנהג המחובר (הנסיעות שלי)."""
        status_enum = RideStatus(status) if status else None
        rides = await crud_ride.get_by_driver_id(db, driver_id, status_enum)
        return [RideMapper.to_response(r) for r in rides]

    async def get_rides_by_group_id(self, db: AsyncSession, group_id: UUID) -> list[RideResponse]:
        """רשימת נסיעות של קבוצה (לטאב נסיעות במסך קבוצה). לא בודק חברות – יש לקרוא רק אחרי אימות שהמשתמש חבר בקבוצה."""
        rides = await crud_ride.get_by_group_id(db, group_id, exclude_cancelled=True)
        return [RideMapper.to_response(r) for r in rides]

    # --- Update (partial) ---

    async def update_ride(
        self,
        db: AsyncSession,
        ride_id: UUID,
        driver_id: UUID,
        payload: RideUpdate,
    ) -> RideResponse:
        """עדכון חלקי – זמן יציאה ו/או מספר מושבים. רק הנהג בעלים."""
        update_dict: dict[str, Any] = {}
        if payload.departure_time is not None:
            update_dict["departure_time"] = payload.departure_time
        if payload.available_seats is not None:
            update_dict["available_seats"] = payload.available_seats
        if not update_dict:
            raise LinkupError(
                message="נדרש לפחות שדה אחד לעדכון (departure_time או available_seats)",
                status_code=400,
                error_code="RIDE_UPDATE_EMPTY_FIELDS",
            )
        ride = await crud_ride.update_partial(db, ride_id, driver_id, **update_dict)
        if not ride:
            raise RideNotFoundError(ride_id)
        await publish_ride_event(ride_id, "RIDE_UPDATED", {"status": ride.status.value})
        try:
            broadcast_payload = _RideNotificationFactory.create_broadcast_payload(ride, RideBroadcastAction.UPDATED.value)
            broadcast_payload["ride_id"] = str(ride_id)
            await broadcast.publish(RIDES_LIST_CHANNEL, json.dumps(broadcast_payload))
        except Exception as e:
            logger.warning("Broadcast ride updated failed: %s", e)
        return RideMapper.to_response(ride)

    # --- Start / End ride (GPS tracking) ---

    async def start_ride(self, db: AsyncSession, ride_id: UUID, driver_id: UUID) -> RideResponse:
        """מעביר נסיעה לסטטוס ACTIVE. דורש לפחות הזמנה אחת מאושרת."""
        try:
            ride = await crud_ride.get_for_update(db, ride_id=ride_id, driver_id=driver_id)
            if not ride:
                raise RideNotFoundError(ride_id)
            if ride.status not in (RideStatus.OPEN, RideStatus.FULL):
                raise InvalidRideStatusError(ride.status.value, action="start_ride")
            confirmed = await crud_booking.get_ride_bookings_by_status_async(db, ride_id, BookingStatus.CONFIRMED.value)
            if not confirmed:
                raise NoConfirmedBookingsError(ride_id=ride_id)
            updated = await crud_ride.update_status(db, ride_id, RideStatus.ACTIVE)
            await db.commit()
            await db.refresh(updated)
        except Exception:
            await db.rollback()
            raise

        await publish_ride_event(
            ride_id,
            "RIDE_STARTED",
            {"status": RideStatus.ACTIVE.value},
        )
        return RideMapper.to_response(updated)

    async def end_ride(self, db: AsyncSession, ride_id: UUID, driver_id: UUID) -> RideResponse:
        """מעביר נסיעה לסטטוס COMPLETED."""
        try:
            ride = await crud_ride.get_for_update(db, ride_id=ride_id, driver_id=driver_id)
            if not ride:
                raise RideNotFoundError(ride_id)
            if ride.status != RideStatus.ACTIVE:
                raise InvalidRideStatusError(ride.status.value, action="end_ride")
            updated = await crud_ride.update_status(db, ride_id, RideStatus.COMPLETED)
            await db.commit()
            await db.refresh(updated)
        except Exception:
            await db.rollback()
            raise

        await publish_ride_event(
            ride_id,
            "RIDE_ENDED",
            {"status": RideStatus.COMPLETED.value},
        )
        return RideMapper.to_response(updated)

    # --- Cancel ---

    async def cancel_ride_by_driver(self, db: AsyncSession, ride_id: UUID, driver_id: UUID) -> None:
        """ביטול נסיעה על ידי הנהג. לוגיקה ב-crud, Outbox נשאר כאן."""
        ride = await crud_ride.get_for_update(db, ride_id=ride_id, driver_id=driver_id)
        if not ride:
            raise RideNotFoundError(ride_id)
        if ride.status == RideStatus.CANCELLED:
            raise RideAlreadyCancelledError()
        origin_name = getattr(ride, "origin_name", None) or "—"
        destination_name = getattr(ride, "destination_name", None) or "—"
        try:
            await crud_booking.cancel_ride_and_bookings(db, ride_id, driver_id)
            await publish_to_outbox(
                db,
                NotificationEvent.RIDE_CANCELLED_BY_DRIVER.value,
                {"ride_id": str(ride_id)},
                [DispatchTarget.RABBITMQ.value],
            )
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        await publish_ride_event(
            ride_id,
            "RIDE_CANCELLED",
            {"status": RideStatus.CANCELLED.value},
        )
        try:
            payload = {
                "event": "RIDE_CANCELLED",
                "ride_id": str(ride_id),
                "status": RideStatus.CANCELLED.value,
                "color": "red",
                "message": f"הנסיעה בוטלה (מ-{origin_name} ל-{destination_name})",
            }
            await broadcast.publish(RIDES_LIST_CHANNEL, json.dumps(payload))
        except Exception as e:
            logger.warning("Broadcast rides list failed after cancel: %s", e)
