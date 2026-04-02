# app/domain/bookings/router.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    WebSocket,
    WebSocketDisconnect,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.api.dependencies.auth import get_current_user, get_current_user_ws, WsUser
from app.domain.users.model import User
from app.domain.bookings.service import BookingService
from app.domain.bookings.crud import crud_booking
from app.domain.bookings.schema import (
    BookingResponse,
    BookingCreate,
    RideManifestResponse,
)
from app.domain.bookings.enum import BookingStatus
from app.domain.rides.enum import RideStatus
from app.domain.geo.schema import (
    DriverLocationReport,
    LocationUpdate,
    PassengerLocationReport,
)
from app.infrastructure.location.location_service import (
    broadcast_location_to_participants,
    broadcast_passenger_location_to_driver,
)
from app.infrastructure.redis.keys import get_booking_channel
from app.infrastructure.redis.broadcast import broadcast
from app.core.exceptions.booking import ForbiddenRideActionError

router = APIRouter(tags=["Bookings"])


@router.post(
    "/request-to-join",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_to_join(
    booking_in: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """בקשת הצטרפות לנסיעה. request_id חייב להיות של המשתמש המחובר."""
    try:
        return await BookingService.request_to_join(
            db,
            ride_id=booking_in.ride_id,
            request_id=booking_in.request_id,
            num_seats=booking_in.num_seats,
            current_user_id=current_user.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{booking_id}/approve", response_model=BookingResponse)
async def approve_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.approve_booking(db, booking_id, current_user.user_id)


@router.patch("/{booking_id}/reject", response_model=BookingResponse)
async def reject_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await BookingService.reject_booking(db, booking_id=booking_id, driver_id=current_user.user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.cancel_booking(db, booking_id, current_user.user_id)


@router.get("/my-bookings", response_model=List[BookingResponse])
async def get_user_bookings(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await BookingService.get_user_bookings(db, user_id=current_user.user_id, status=status, page=1, limit=50)
    return result.items


@router.get("/ride/{ride_id}/manifest", response_model=RideManifestResponse)
async def get_ride_manifest(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.get_ride_manifest(db, ride_id, current_user.user_id)


@router.get("/ride/{ride_id}/pending", response_model=List[BookingResponse])
async def get_pending_requests(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.get_pending_requests(db, ride_id, current_user.user_id)


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = await BookingService.get_booking(db, booking_id)
    if str(booking.passenger_id) != str(current_user.user_id) and str(booking.ride.driver_id) != str(current_user.user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="גישה חסומה")
    return booking


@router.post("/{booking_id}/location", status_code=status.HTTP_204_NO_CONTENT)
async def report_driver_location(
    booking_id: UUID,
    body: DriverLocationReport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    הנהג מדווח על המיקום בנסיעה. משודר לנוסעים המאושרים ב-WebSocket.
    דורש: נהג הנסיעה, נסיעה בסטטוס active.
    """
    booking = await BookingService.get_booking(db, booking_id)
    if not booking or not booking.ride:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if str(booking.ride.driver_id) != str(current_user.user_id):
        raise ForbiddenRideActionError("גישה חסומה – רק נהג הנסיעה יכול לדווח מיקום")
    if booking.ride.status != RideStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ניתן לדווח מיקום רק בנסיעה פעילה (active)",
        )
    confirmed = await crud_booking.get_ride_bookings_by_status_async(db, booking.ride_id, BookingStatus.CONFIRMED)
    involved = [b.booking_id for b in confirmed]
    location_in = LocationUpdate(
        booking_id=0,
        lat=body.lat,
        lon=body.lng,
        heading=body.heading or 0.0,
        speed=body.speed or 0.0,
    )
    await broadcast_location_to_participants(location_in, booking.ride_id, involved)
    return None


@router.post("/{booking_id}/passenger-location", status_code=status.HTTP_204_NO_CONTENT)
async def report_passenger_location(
    booking_id: UUID,
    body: PassengerLocationReport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    נוסע מדווח מיקום בנסיעה. משודר לנהג בערוץ ride_{ride_id}:passenger_locations.
    דורש: הנוסע של הבוקינג.
    """
    booking = await BookingService.get_booking(db, booking_id)
    if not booking or not booking.ride:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if str(booking.passenger_id) != str(current_user.user_id):
        raise ForbiddenRideActionError("גישה חסומה – רק הנוסע של ההזמנה יכול לדווח מיקום")
    await broadcast_passenger_location_to_driver(
        ride_id=booking.ride_id,
        booking_id=booking.booking_id,
        passenger_id=current_user.user_id,
        lat=body.lat,
        lng=body.lng,
        heading=body.heading or 0.0,
        speed=body.speed or 0.0,
    )
    return None


@router.websocket("/ws/{booking_id}/location")
async def booking_location_websocket(
    websocket: WebSocket,
    booking_id: UUID,
    user: Optional[WsUser] = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db),
):
    """
    ערוץ WebSocket לעדכוני מיקום נהג עבור בוקינג. רק הנוסע של הבוקינג יכול להתחבר.
    חיבור: GET /api/v1/bookings/ws/{booking_id}/location?token=JWT
    """
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    booking = await BookingService.get_booking(db, booking_id)
    if not booking:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if str(booking.passenger_id) != str(user.user_id):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    channel_name = get_booking_channel(booking_id)
    try:
        async with broadcast.subscribe(channel=channel_name) as subscriber:
            async for event in subscriber:
                await websocket.send_text(event.message)
    except WebSocketDisconnect:
        pass
