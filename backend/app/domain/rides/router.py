import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.dependencies.auth import WsUser, get_current_user, get_current_user_ws
from app.api.dependencies.group_membership import verify_group_membership
from app.api.dependencies.rate_limit import rate_limit_rides
from app.api.dependencies.services import get_ride_service
from app.core.exceptions.ride import RideNotFoundError
from app.db.session import get_db
from app.domain.rides.schema import (
    PaginatedRidesResponse,
    RideCreate,
    RidePreviewCreate,
    RidePreviewResponse,
    RideResponse,
    RideUpdate,
)
from app.domain.rides.service import RideService
from app.domain.users.model import User
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.keys import get_ride_channel, get_ride_passengers_channel

logger = logging.getLogger(__name__)
router = APIRouter()


# --- HTTP routes ---
@router.post("/preview-routes", response_model=RidePreviewResponse)
async def preview_ride_options(
    preview_in: RidePreviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
    _: None = Depends(rate_limit_rides),
):
    """Step 1: route options and metrics for ride preview."""
    return await ride_svc.get_ride_preview(preview_in)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=RideResponse)
async def create_new_ride(
    ride_in: RideCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
    _: None = Depends(rate_limit_rides),
):
    if ride_in.group_id is not None:
        await verify_group_membership(db, ride_in.group_id, current_user.user_id)
    return await ride_svc.create_ride(db=db, ride_in=ride_in, current_user_id=current_user.user_id)


@router.get("/me", response_model=PaginatedRidesResponse)
async def get_my_rides(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: str | None = Query(
        None,
        description="סנן לפי סטטוס: open, full, active, completed, cancelled",
    ),
    limit: int = Query(20, ge=1, le=100),
    after: str | None = Query(None),
    ride_svc: RideService = Depends(get_ride_service),
):
    """List current user's rides as driver."""
    return await ride_svc.get_my_rides(
        db,
        current_user.user_id,
        status=status,
        limit=limit,
        after=after,
    )


@router.patch("/{ride_id}", response_model=RideResponse)
async def update_ride(
    ride_id: UUID,
    payload: RideUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    """Partial ride update: departure and/or seats (driver owner only)."""
    return await ride_svc.update_ride(db, ride_id, current_user.user_id, payload)


@router.post("/{ride_id}/start", response_model=RideResponse)
async def start_ride(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    """Start ride → ACTIVE; requires at least one confirmed passenger."""
    return await ride_svc.start_ride(db, ride_id=ride_id, driver_id=current_user.user_id)


@router.post("/{ride_id}/end", response_model=RideResponse)
async def end_ride(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    """End ride → COMPLETED."""
    return await ride_svc.end_ride(db, ride_id=ride_id, driver_id=current_user.user_id)


@router.delete("/{ride_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_ride(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    await ride_svc.cancel_ride_by_driver(
        db=db,
        ride_id=ride_id,
        driver_id=current_user.user_id,
    )


@router.get("/{ride_id}", response_model=RideResponse)
async def read_ride(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    ride = await ride_svc.get_ride_by_id(db, ride_id)
    if not ride:
        raise RideNotFoundError(ride_id)
    return ride


# --- WebSocket ---


@router.websocket("/ws/{ride_id}")
async def ride_status_websocket(
    websocket: WebSocket,
    ride_id: UUID,
    user: WsUser | None = Depends(get_current_user_ws),
):
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    channel_name = get_ride_channel(ride_id)
    logger.info("Client connected to WebSocket for ride: %s", ride_id)

    try:
        async with broadcast.subscribe(channel=channel_name) as subscriber:
            async for event in subscriber:
                await websocket.send_text(event.message)

    except WebSocketDisconnect:
        logger.info("Client disconnected from ride %s", ride_id)


@router.websocket("/ws/{ride_id}/passengers")
async def ride_passengers_locations_websocket(
    websocket: WebSocket,
    ride_id: UUID,
    user: WsUser | None = Depends(get_current_user_ws),
    db: AsyncSession = Depends(get_db),
    ride_svc: RideService = Depends(get_ride_service),
):
    """
    WebSocket channel for passenger location updates on a ride. Only the ride driver may connect.
    Connect: GET /api/v1/rides/ws/{ride_id}/passengers?token=JWT
    """
    if not user:
        logger.warning("WS passengers: no user, closing")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    ride = await ride_svc.get_ride_by_id(db, ride_id)
    logger.info(
        "WS passengers: ride=%s user=%s driver=%s",
        ride_id,
        getattr(user, "user_id", None),
        getattr(ride, "driver_id", None) if ride else "NONE",
    )
    if not ride or str(ride.driver_id) != str(user.user_id):
        logger.warning(
            "WS passengers: auth failed, ride=%s user=%s",
            ride_id,
            getattr(user, "user_id", None),
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    channel_name = get_ride_passengers_channel(ride_id)
    try:
        async with broadcast.subscribe(channel=channel_name) as subscriber:
            async for event in subscriber:
                await websocket.send_text(event.message)
    except WebSocketDisconnect:
        logger.info(f"Driver disconnected from passengers stream for ride {ride_id}")
