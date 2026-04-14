# app/domain/bookings/router.py
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import WsUser, get_current_user, get_current_user_ws
from app.core.exceptions.booking import ForbiddenRideActionError
from app.core.exceptions.validation import BadRequestError
from app.db.session import get_db
from app.domain.bookings.schema import (
    BookingCreate,
    BookingResponse,
    DriverSummaryResponse,
    PassengerSummaryResponse,
    RideManifestResponse,
)
from app.domain.bookings.service import BookingService
from app.domain.geo.schema import (
    DriverLocationReport,
    PassengerLocationReport,
)
from app.domain.users.model import User
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.keys import get_booking_channel

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
    """Request to join a ride. request_id must belong to the authenticated user."""
    try:
        return await BookingService.request_to_join(
            db,
            ride_id=booking_in.ride_id,
            request_id=booking_in.request_id,
            num_seats=booking_in.num_seats,
            current_user_id=current_user.user_id,
        )
    except ValueError as e:
        raise BadRequestError(str(e)) from e


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
        raise BadRequestError(str(e)) from e


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.cancel_booking(db, booking_id, current_user.user_id)


@router.get("/my-bookings", response_model=list[BookingResponse])
async def get_user_bookings(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await BookingService.get_user_bookings(db, user_id=current_user.user_id, status=status, page=1, limit=50)
    return result.items


@router.get("/driver-summary", response_model=DriverSummaryResponse)
async def get_driver_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Driver rides with embedded passengers — replaces N+1 fetchRideManifest loop."""
    return await BookingService.get_driver_summary(db, current_user.user_id)


@router.get("/passenger-summary", response_model=PassengerSummaryResponse)
async def get_passenger_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Passenger bookings with embedded ride + driver — replaces N+1 fetchRideById loop."""
    return await BookingService.get_passenger_summary(db, current_user.user_id)


@router.get("/ride/{ride_id}/manifest", response_model=RideManifestResponse)
async def get_ride_manifest(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.get_ride_manifest(db, ride_id, current_user.user_id)


@router.get("/ride/{ride_id}/pending", response_model=list[BookingResponse])
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
        raise ForbiddenRideActionError("גישה חסומה")
    return booking


@router.post("/{booking_id}/location", status_code=status.HTTP_204_NO_CONTENT)
async def report_driver_location(
    booking_id: UUID,
    body: DriverLocationReport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Driver reports location during the ride. Broadcast to confirmed passengers over WebSocket.
    Requires: ride driver, ride in active status.
    """
    await BookingService.broadcast_driver_location(db, booking_id, current_user.user_id, body)
    return


@router.post("/{booking_id}/passenger-location", status_code=status.HTTP_204_NO_CONTENT)
async def report_passenger_location(
    booking_id: UUID,
    body: PassengerLocationReport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Passenger reports location during the ride. Broadcast to driver on ride_{ride_id}:passenger_locations.
    Requires: the booking’s passenger.
    """
    await BookingService.broadcast_passenger_location(db, booking_id, current_user.user_id, body)
    return


@router.websocket("/ws/{booking_id}/location")
async def booking_location_websocket(
    websocket: WebSocket,
    booking_id: UUID,
    user: WsUser | None = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket channel for driver location updates for a booking. Only the booking passenger may connect.
    Connect: GET /api/v1/bookings/ws/{booking_id}/location?token=JWT
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
