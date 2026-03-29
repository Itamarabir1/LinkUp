import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.admin import get_current_admin_user
from app.api.dependencies.services import get_ride_service
from app.db.session import get_db
from app.domain.groups.model import Group, GroupMember
from app.domain.rides.crud import crud_ride
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride
from app.domain.rides.service import RideService
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.infrastructure.health.health_service import check_health
from app.infrastructure.outbox.model import OutboxEvent
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Admin"])


def _audit(actor: User, action: str, detail: str) -> None:
    logger.info(
        "[admin_audit] actor_id=%s email=%s action=%s detail=%s ts=%s",
        actor.user_id,
        actor.email,
        action,
        detail,
        datetime.now(timezone.utc).isoformat(),
    )


@router.get("/me")
async def admin_me(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return {
        "user_id": str(current_user.user_id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": bool(current_user.is_admin),
    }


@router.get("/health")
async def admin_health(current_user: User = Depends(get_current_admin_user)):
    return await check_health()


def _enum_key(v) -> str:
    return v.value if hasattr(v, "value") else str(v)


@router.get("/stats")
async def admin_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Aggregates for admin dashboard (single round-trip)."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    users_total = await db.scalar(select(func.count()).select_from(User))
    rides_active = await db.scalar(
        select(func.count())
        .select_from(Ride)
        .where(
            Ride.status.in_(
                [RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE]
            )
        )
    )
    bookings_total = await db.scalar(select(func.count()).select_from(Booking))
    outbox_pending = await db.scalar(
        select(func.count())
        .select_from(OutboxEvent)
        .where(OutboxEvent.status == "PENDING")
    )

    users_new_today = await db.scalar(
        select(func.count()).select_from(User).where(User.created_at >= today_start)
    )
    rides_total = await db.scalar(select(func.count()).select_from(Ride))
    bookings_pending = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status == BookingStatus.PENDING)
    )
    bookings_confirmed = await db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(Booking.status == BookingStatus.CONFIRMED)
    )
    groups_total = await db.scalar(select(func.count()).select_from(Group))
    outbox_failed = await db.scalar(
        select(func.count())
        .select_from(OutboxEvent)
        .where(OutboxEvent.status == "FAILED")
    )
    active_users_last_7_days = await db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.last_active_at >= week_ago)
    )

    rides_by_status_result = await db.execute(
        select(Ride.status, func.count()).group_by(Ride.status)
    )
    rides_by_status = {
        _enum_key(row[0]): int(row[1]) for row in rides_by_status_result.all()
    }

    bookings_by_status_result = await db.execute(
        select(Booking.status, func.count()).group_by(Booking.status)
    )
    bookings_by_status = {
        _enum_key(row[0]): int(row[1]) for row in bookings_by_status_result.all()
    }

    users_per_day: list[dict] = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(days=1)
        count = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                and_(User.created_at >= day_start, User.created_at < day_end)
            )
        )
        users_per_day.append(
            {"date": day_start.strftime("%d/%m"), "count": int(count or 0)}
        )

    return {
        "users_total": int(users_total or 0),
        "rides_active": int(rides_active or 0),
        "bookings_total": int(bookings_total or 0),
        "outbox_pending": int(outbox_pending or 0),
        "users_new_today": int(users_new_today or 0),
        "rides_total": int(rides_total or 0),
        "bookings_pending": int(bookings_pending or 0),
        "bookings_confirmed": int(bookings_confirmed or 0),
        "groups_total": int(groups_total or 0),
        "outbox_failed": int(outbox_failed or 0),
        "active_users_last_7_days": int(active_users_last_7_days or 0),
        "rides_by_status": rides_by_status,
        "bookings_by_status": bookings_by_status,
        "users_per_day": users_per_day,
    }


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


@router.patch("/users/{user_id}/active")
async def admin_toggle_user_active(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    u = await crud_user.get_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = not bool(u.is_active)
    await db.commit()
    await db.refresh(u)
    _audit(
        current_user,
        "toggle_user_active",
        f"target={user_id} is_active={u.is_active}",
    )
    return {"user_id": str(u.user_id), "is_active": bool(u.is_active)}


@router.patch("/users/{user_id}/admin")
async def admin_toggle_user_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    u = await crud_user.get_by_id(db, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_admin = not bool(u.is_admin)
    await db.commit()
    await db.refresh(u)
    _audit(
        current_user,
        "toggle_user_admin",
        f"target={user_id} is_admin={u.is_admin}",
    )
    return {"user_id": str(u.user_id), "is_admin": bool(u.is_admin)}


@router.get("/rides")
async def admin_rides(
    status: str | None = Query(
        default=None,
        description="Filter: active | completed | cancelled (omit = all recent)",
    ),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = crud_ride._base_ride_stmt()
    if status == "active":
        stmt = stmt.where(
            Ride.status.in_([RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE])
        )
    elif status == "completed":
        stmt = stmt.where(Ride.status == RideStatus.COMPLETED)
    elif status == "cancelled":
        stmt = stmt.where(Ride.status == RideStatus.CANCELLED)
    stmt = stmt.order_by(Ride.departure_time.desc()).limit(limit)
    result = await db.execute(stmt)
    rides = list(result.scalars().all())
    out = []
    for r in rides:
        st = getattr(r.status, "value", None) or str(r.status)
        driver_name = ""
        if r.driver:
            driver_name = r.driver.full_name or ""
        out.append(
            {
                "ride_id": str(r.ride_id),
                "driver_id": str(r.driver_id),
                "driver_name": driver_name,
                "origin_name": r.origin_name,
                "destination_name": r.destination_name,
                "departure_time": r.departure_time.isoformat()
                if r.departure_time
                else None,
                "status": st,
                "available_seats": r.available_seats,
                "group_id": str(r.group_id) if r.group_id else None,
            }
        )
    return out


@router.post("/rides/{ride_id}/cancel")
async def admin_cancel_ride(
    ride_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    ride = await crud_ride.get_async(db, ride_id)
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    await ride_svc.cancel_ride_by_driver(db, ride_id, ride.driver_id)
    _audit(current_user, "cancel_ride", f"ride_id={ride_id}")
    return {"ok": True, "ride_id": str(ride_id)}


@router.get("/groups")
async def admin_groups(
    limit: int = Query(default=200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    member_sq = (
        select(
            GroupMember.group_id.label("group_id"),
            func.count(GroupMember.id).label("member_count"),
        )
        .group_by(GroupMember.group_id)
        .subquery()
    )
    stmt = (
        select(Group, member_sq.c.member_count)
        .outerjoin(member_sq, Group.group_id == member_sq.c.group_id)
        .options(selectinload(Group.admin))
        .order_by(Group.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    items = []
    for row in rows:
        g, mc = row[0], row[1]
        admin_name = ""
        admin_email = None
        if g.admin:
            admin_name = g.admin.full_name or ""
            admin_email = g.admin.email
        items.append(
            {
                "group_id": str(g.group_id),
                "name": g.name,
                "member_count": int(mc or 0),
                "admin_id": str(g.admin_id),
                "admin_name": admin_name,
                "admin_email": admin_email,
                "is_active": bool(g.is_active),
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
        )
    return items


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


@router.post("/outbox/{event_id}/requeue")
async def admin_outbox_requeue(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
    result = await db.execute(stmt)
    e = result.scalars().first()
    if not e:
        raise HTTPException(status_code=404, detail="Outbox event not found")
    if e.status != "FAILED":
        raise HTTPException(
            status_code=400, detail="Only FAILED events can be requeued"
        )
    await db.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(
            status="PENDING",
            last_error=None,
            processed_at=None,
        )
    )
    await db.commit()
    _audit(current_user, "outbox_requeue", f"event_id={event_id}")
    return {"ok": True, "id": str(event_id), "status": "PENDING"}


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
