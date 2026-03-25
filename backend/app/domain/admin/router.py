from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from uuid import UUID

from app.api.dependencies.admin import get_current_admin_user
from app.db.session import get_db
from app.domain.users.model import User
from app.infrastructure.health.health_service import check_health
from app.infrastructure.outbox.model import OutboxEvent
from app.domain.rides.model import Ride
from app.domain.bookings.model import Booking

router = APIRouter(tags=["Admin"])


@router.get("/me")
async def admin_me(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    # db kept for symmetry/future extension
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": bool(current_user.is_admin),
    }


@router.get("/health")
async def admin_health(current_user: User = Depends(get_current_admin_user)):
    return await check_health()


@router.get("/users")
async def admin_users(
    q: str | None = Query(default=None, description="Search: email/phone/full_name"),
    is_active: bool | None = Query(default=None),
    is_admin: bool | None = Query(default=None),
    is_verified: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(User)
    if q:
        qq = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                func.coalesce(User.email, "").ilike(qq),
                func.coalesce(User.phone_number, "").ilike(qq),
                func.coalesce(User.full_name, "").ilike(qq),
            )
        )
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if is_admin is not None:
        stmt = stmt.where(User.is_admin == is_admin)
    if is_verified is not None:
        stmt = stmt.where(User.is_verified == is_verified)

    stmt = stmt.order_by(User.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    users = list(result.scalars().all())
    return [
        {
            "user_id": str(u.user_id),
            "full_name": u.full_name,
            "email": u.email,
            "phone_number": u.phone_number,
            "is_active": bool(u.is_active),
            "is_admin": bool(u.is_admin),
            "is_verified": bool(u.is_verified),
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None,
        }
        for u in users
    ]


@router.get("/outbox")
async def admin_outbox(
    status: str | None = Query(default=None, description="PENDING/PROCESSED/FAILED"),
    event_name: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(OutboxEvent)
    if status:
        stmt = stmt.where(OutboxEvent.status == status)
    if event_name:
        stmt = stmt.where(OutboxEvent.event_name == event_name)
    stmt = stmt.order_by(OutboxEvent.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    events = list(result.scalars().all())
    return [
        {
            "id": str(e.id),
            "event_name": e.event_name,
            "status": e.status,
            "retry_count": e.retry_count,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
        }
        for e in events
    ]


@router.get("/outbox/{event_id}")
async def admin_outbox_by_id(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
    result = await db.execute(stmt)
    e = result.scalars().first()
    if not e:
        raise HTTPException(status_code=404, detail="Outbox event not found")
    return {
        "id": str(e.id),
        "event_name": e.event_name,
        "status": e.status,
        "retry_count": e.retry_count,
        "last_error": e.last_error,
        "targets": list(e.targets or []),
        "payload": e.payload,
        "metadata": e.metadata_json,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "processed_at": e.processed_at.isoformat() if e.processed_at else None,
    }


@router.get("/rides/{ride_id}")
async def admin_ride_by_id(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(Ride).where(Ride.ride_id == ride_id)
    result = await db.execute(stmt)
    r = result.scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="Ride not found")
    status_val = getattr(r.status, "value", None) or str(r.status)
    return {
        "ride_id": str(r.ride_id),
        "driver_id": str(r.driver_id),
        "group_id": str(r.group_id) if r.group_id else None,
        "origin_name": r.origin_name,
        "destination_name": r.destination_name,
        "departure_time": r.departure_time.isoformat() if r.departure_time else None,
        "estimated_arrival_time": r.estimated_arrival_time.isoformat()
        if r.estimated_arrival_time
        else None,
        "available_seats": r.available_seats,
        "price": float(r.price) if r.price is not None else None,
        "status": status_val,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/bookings/{booking_id}")
async def admin_booking_by_id(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(Booking).where(Booking.booking_id == booking_id)
    result = await db.execute(stmt)
    b = result.scalars().first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found")
    status_val = getattr(b.status, "value", None) or str(b.status)
    return {
        "booking_id": str(b.booking_id),
        "ride_id": str(b.ride_id),
        "passenger_id": str(b.passenger_id),
        "request_id": str(b.request_id) if b.request_id else None,
        "num_seats": b.num_seats,
        "pickup_name": b.pickup_name,
        "pickup_time": b.pickup_time.isoformat() if b.pickup_time else None,
        "reminder_sent": bool(b.reminder_sent),
        "status": status_val,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }

