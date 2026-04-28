import logging
from json import loads as json_loads
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.admin import get_current_admin_user
from app.core.exceptions.admin import OutboxEventNotFoundError, OutboxRequeueInvalidStatusError
from app.core.exceptions.booking import BookingNotFoundError
from app.core.exceptions.ride import RideNotFoundError
from app.core.exceptions.user import UserNotFoundError
from app.api.dependencies.services import get_ride_service
from app.db.session import get_db
from app.domain.bookings.enum import BookingStatus
from app.domain.bookings.model import Booking
from app.domain.billing.model import Payment, PaymentStatus
from app.domain.groups.model import Group, GroupMember
from app.domain.rides.crud import crud_ride
from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride
from app.domain.rides.service import RideService
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.core.config import settings
from app.infrastructure.health.health_service import check_health
from app.infrastructure.audit.repo import audit_repo
from app.infrastructure.outbox.model import OutboxEvent
from app.infrastructure.rabbitmq.client import outbox_rabbit_client, rabbit_client, worker_rabbit_client
from app.infrastructure.rabbitmq.topology import QUEUE_SPECS

logger = logging.getLogger(__name__)

# Dashboard stats: "active users" window and signups chart (days)
_ADMIN_STATS_ACTIVE_USERS_DAYS = 7
_ADMIN_STATS_CHART_DAYS = 7
# Default pagination for admin endpoints
_QUERY_DEFAULT_USERS_LIMIT = 50
_QUERY_MAX_USERS_LIMIT = 200
_QUERY_DEFAULT_RIDES_LIMIT = 100
_QUERY_DEFAULT_GROUPS_LIMIT = 200
_QUERY_DEFAULT_OUTBOX_LIMIT = 100
_QUERY_MAX_ADMIN_LIST_LIMIT = 500

router = APIRouter(tags=["Admin"])


def _audit(actor: User, action: str, detail: str) -> None:
    logger.info(
        "[admin_audit] actor_id=%s email=%s action=%s detail=%s ts=%s",
        actor.user_id,
        actor.email,
        action,
        detail,
        datetime.now(UTC).isoformat(),
    )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _admin_caps_for(user: User) -> set[str]:
    """
    Incremental capability model:
    - If ADMIN_CAPABILITIES_JSON is unset/invalid -> full admin access ("*")
    - If set, expected JSON map: {"email@example.com": ["admin.billing.read", ...]}
    """
    raw = (getattr(settings, "ADMIN_CAPABILITIES_JSON", None) or "").strip()
    if not raw:
        return {"*"}
    try:
        parsed = json_loads(raw)
        if not isinstance(parsed, dict):
            return {"*"}
        caps = parsed.get(_normalize_email(user.email), ["*"])
        if not isinstance(caps, list):
            return {"*"}
        return {str(c).strip() for c in caps if str(c).strip()}
    except Exception:
        return {"*"}


def _require_capability(user: User, capability: str) -> None:
    caps = _admin_caps_for(user)
    if "*" in caps or capability in caps:
        return
    raise HTTPException(status_code=403, detail=f"Missing admin capability: {capability}")


def _paginated(*, items: list, limit: int, offset: int, total: int) -> dict:
    next_offset = offset + limit if (offset + limit) < total else None
    return {
        "items": items,
        "limit": limit,
        "offset": offset,
        "total": total,
        "next_offset": next_offset,
    }


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
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=_ADMIN_STATS_ACTIVE_USERS_DAYS)

    users_total = await db.scalar(select(func.count()).select_from(User))
    rides_active = await db.scalar(
        select(func.count()).select_from(Ride).where(Ride.status.in_([RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE])),
    )
    bookings_total = await db.scalar(select(func.count()).select_from(Booking))
    outbox_pending = await db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "PENDING"))

    users_new_today = await db.scalar(select(func.count()).select_from(User).where(User.created_at >= today_start))
    rides_total = await db.scalar(select(func.count()).select_from(Ride))
    bookings_pending = await db.scalar(select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.PENDING))
    bookings_confirmed = await db.scalar(select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.CONFIRMED))
    groups_total = await db.scalar(select(func.count()).select_from(Group))
    outbox_failed = await db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "FAILED"))
    active_users_last_7_days = await db.scalar(select(func.count()).select_from(User).where(User.last_active_at >= week_ago))

    rides_by_status_result = await db.execute(select(Ride.status, func.count()).group_by(Ride.status))
    rides_by_status = {_enum_key(row[0]): int(row[1]) for row in rides_by_status_result.all()}

    bookings_by_status_result = await db.execute(select(Booking.status, func.count()).group_by(Booking.status))
    bookings_by_status = {_enum_key(row[0]): int(row[1]) for row in bookings_by_status_result.all()}

    users_per_day: list[dict] = []
    for i in range(_ADMIN_STATS_CHART_DAYS - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = await db.scalar(select(func.count()).select_from(User).where(and_(User.created_at >= day_start, User.created_at < day_end)))
        users_per_day.append({"date": day_start.strftime("%d/%m"), "count": int(count or 0)})

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
    limit: int = Query(default=_QUERY_DEFAULT_USERS_LIMIT, ge=1, le=_QUERY_MAX_USERS_LIMIT),
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
            ),
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
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    u = await crud_user.get_by_id(db, user_id)
    if not u:
        raise UserNotFoundError(identifier=str(user_id))
    u.is_active = not bool(u.is_active)
    await audit_repo.record(
        db,
        actor_user_id=current_user.user_id,
        action="toggle_user_active",
        resource_type="user",
        resource_id=str(user_id),
        metadata={"is_active": bool(u.is_active)},
        ip_address=_client_ip(request),
    )
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
    request: Request,
    action: str | None = Query(default=None, description="grant | revoke | toggle (default)"),
    reason: str | None = Query(default=None, description="Optional audit reason"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    u = await crud_user.get_by_id(db, user_id)
    if not u:
        raise UserNotFoundError(identifier=str(user_id))
    normalized_action = (action or "toggle").strip().lower()
    if normalized_action not in {"toggle", "grant", "revoke"}:
        raise HTTPException(status_code=400, detail="Invalid action. Use grant, revoke, or toggle.")

    before_is_admin = bool(u.is_admin)
    if normalized_action == "grant":
        next_is_admin = True
    elif normalized_action == "revoke":
        next_is_admin = False
    else:
        next_is_admin = not before_is_admin

    if before_is_admin and not next_is_admin and u.user_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Self-demotion is not allowed.")

    if before_is_admin and not next_is_admin:
        admin_count = await db.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True)))
        if int(admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="At least one admin must remain.")

    u.is_admin = next_is_admin
    after_is_admin = bool(u.is_admin)
    changed = before_is_admin != after_is_admin
    audit_action = (
        "grant_user_admin"
        if (not before_is_admin and after_is_admin)
        else "revoke_user_admin"
        if (before_is_admin and not after_is_admin)
        else "toggle_user_admin_noop"
    )
    await audit_repo.record(
        db,
        actor_user_id=current_user.user_id,
        action=audit_action,
        resource_type="user",
        resource_id=str(user_id),
        metadata={
            "target_email": u.email,
            "before_is_admin": before_is_admin,
            "after_is_admin": after_is_admin,
            "changed": changed,
            "requested_action": normalized_action,
            "reason": reason,
        },
        ip_address=_client_ip(request),
    )
    await db.commit()
    await db.refresh(u)
    _audit(
        current_user,
        audit_action,
        f"target={user_id} before={before_is_admin} after={after_is_admin} changed={changed}",
    )
    return {
        "user_id": str(u.user_id),
        "is_admin": bool(u.is_admin),
        "before_is_admin": before_is_admin,
        "after_is_admin": after_is_admin,
        "changed": changed,
        "action": normalized_action,
    }


@router.get("/rides")
async def admin_rides(
    status: str | None = Query(
        default=None,
        description="Filter: active | completed | cancelled (omit = all recent)",
    ),
    limit: int = Query(default=_QUERY_DEFAULT_RIDES_LIMIT, ge=1, le=_QUERY_MAX_ADMIN_LIST_LIMIT),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = crud_ride._base_ride_stmt()
    if status == "active":
        stmt = stmt.where(Ride.status.in_([RideStatus.OPEN, RideStatus.FULL, RideStatus.ACTIVE]))
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
                "departure_time": r.departure_time.isoformat() if r.departure_time else None,
                "status": st,
                "available_seats": r.available_seats,
                "group_id": str(r.group_id) if r.group_id else None,
            },
        )
    return out


@router.post("/rides/{ride_id}/cancel")
async def admin_cancel_ride(
    ride_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
    ride_svc: RideService = Depends(get_ride_service),
):
    ride = await crud_ride.get_async(db, ride_id)
    if not ride:
        raise RideNotFoundError(ride_id)
    await ride_svc.cancel_ride_by_driver(db, ride_id, ride.driver_id)
    await audit_repo.record(
        db,
        actor_user_id=current_user.user_id,
        action="cancel_ride",
        resource_type="ride",
        resource_id=str(ride_id),
        metadata={"driver_id": str(ride.driver_id)},
        ip_address=_client_ip(request),
    )
    await db.commit()
    _audit(current_user, "cancel_ride", f"ride_id={ride_id}")
    return {"ok": True, "ride_id": str(ride_id)}


@router.get("/groups")
async def admin_groups(
    limit: int = Query(default=_QUERY_DEFAULT_GROUPS_LIMIT, ge=1, le=_QUERY_MAX_ADMIN_LIST_LIMIT),
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
            },
        )
    return items


@router.get("/bookings")
async def admin_bookings(
    status: str | None = Query(default=None),
    ride_id: UUID | None = Query(default=None),
    passenger_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=_QUERY_MAX_ADMIN_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.bookings.read")
    query = select(Booking)
    if status:
        query = query.where(Booking.status == status)
    if ride_id:
        query = query.where(Booking.ride_id == ride_id)
    if passenger_id:
        query = query.where(Booking.passenger_id == passenger_id)
    total = int((await db.scalar(select(func.count()).select_from(query.subquery()))) or 0)
    result = await db.execute(query.order_by(Booking.created_at.desc()).offset(offset).limit(limit))
    rows = list(result.scalars().all())
    items = [
        {
            "booking_id": str(b.booking_id),
            "ride_id": str(b.ride_id),
            "passenger_id": str(b.passenger_id),
            "request_id": str(b.request_id) if b.request_id else None,
            "num_seats": b.num_seats,
            "pickup_name": b.pickup_name,
            "pickup_time": b.pickup_time.isoformat() if b.pickup_time else None,
            "status": getattr(b.status, "value", None) or str(b.status),
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "updated_at": b.updated_at.isoformat() if b.updated_at else None,
        }
        for b in rows
    ]
    return _paginated(items=items, limit=limit, offset=offset, total=total)


@router.get("/billing/payments")
async def admin_billing_payments(
    status: str | None = Query(default=None),
    user_id: UUID | None = Query(default=None),
    currency: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=_QUERY_MAX_ADMIN_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.billing.read")
    query = select(Payment)
    if status:
        query = query.where(Payment.status == status)
    if user_id:
        query = query.where(Payment.user_id == user_id)
    if currency:
        query = query.where(Payment.currency == currency.lower())
    total = int((await db.scalar(select(func.count()).select_from(query.subquery()))) or 0)
    result = await db.execute(query.order_by(Payment.created_at.desc()).offset(offset).limit(limit))
    rows = list(result.scalars().all())
    items = [
        {
            "payment_id": str(p.payment_id),
            "user_id": str(p.user_id),
            "amount": float(p.amount),
            "currency": p.currency,
            "status": getattr(p.status, "value", None) or str(p.status),
            "stripe_payment_intent_id": p.stripe_payment_intent_id,
            "stripe_session_id": p.stripe_session_id,
            "stripe_event_id": p.stripe_event_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in rows
    ]
    return _paginated(items=items, limit=limit, offset=offset, total=total)


@router.get("/billing/payments/{payment_id}")
async def admin_billing_payment_by_id(
    payment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.billing.read")
    payment = (await db.execute(select(Payment).where(Payment.payment_id == payment_id))).scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "payment_id": str(payment.payment_id),
        "user_id": str(payment.user_id),
        "amount": float(payment.amount),
        "currency": payment.currency,
        "status": getattr(payment.status, "value", None) or str(payment.status),
        "stripe_payment_intent_id": payment.stripe_payment_intent_id,
        "stripe_session_id": payment.stripe_session_id,
        "stripe_event_id": payment.stripe_event_id,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "updated_at": payment.updated_at.isoformat() if payment.updated_at else None,
    }


@router.get("/outbox")
async def admin_outbox(
    status: str | None = Query(default=None, description="PENDING/PROCESSED/FAILED"),
    event_name: str | None = Query(default=None),
    limit: int = Query(default=_QUERY_DEFAULT_OUTBOX_LIMIT, ge=1, le=_QUERY_MAX_ADMIN_LIST_LIMIT),
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


@router.get("/audit-log")
async def admin_audit_log(
    actor_user_id: UUID | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=_QUERY_MAX_ADMIN_LIST_LIMIT),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.audit.read")
    from app.infrastructure.audit.model import AuditLog  # local import to avoid cycle

    query = select(AuditLog)
    if actor_user_id is not None:
        query = query.where(AuditLog.actor_user_id == actor_user_id)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if action:
        query = query.where(AuditLog.action == action)
    if created_from:
        query = query.where(AuditLog.created_at >= created_from)
    if created_to:
        query = query.where(AuditLog.created_at <= created_to)

    total_stmt = select(func.count()).select_from(query.subquery())
    total = int((await db.scalar(total_stmt)) or 0)
    rows = list(
        (
            await db.execute(
                query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit),
            )
        )
        .scalars()
        .all(),
    )
    items = [
        {
            "id": str(r.id),
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "metadata": r.metadata_json,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    await audit_repo.record(
        db,
        actor_user_id=current_user.user_id,
        action="admin_audit_log_read",
        resource_type="audit_log",
        resource_id=None,
        metadata={
            "limit": limit,
            "offset": offset,
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "resource_type": resource_type,
            "action_filter": action,
            "created_from": created_from.isoformat() if created_from else None,
            "created_to": created_to.isoformat() if created_to else None,
        },
        ip_address=None,
    )
    await db.commit()
    return _paginated(items=items, limit=limit, offset=offset, total=total)


@router.get("/outbox/{event_id}")
async def admin_outbox_by_id(
    event_id: UUID,
    include_payload: bool = Query(default=False, description="Include raw payload/metadata (audited sensitive read)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.outbox.read")
    stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
    result = await db.execute(stmt)
    e = result.scalars().first()
    if not e:
        raise OutboxEventNotFoundError(event_id)
    if include_payload:
        await audit_repo.record(
            db,
            actor_user_id=current_user.user_id,
            action="admin_outbox_payload_read",
            resource_type="outbox_event",
            resource_id=str(event_id),
            metadata={"include_payload": True},
            ip_address=None,
        )
        await db.commit()
    return {
        "id": str(e.id),
        "event_name": e.event_name,
        "status": e.status,
        "retry_count": e.retry_count,
        "last_error": e.last_error,
        "targets": list(e.targets or []),
        "payload": e.payload if include_payload else None,
        "metadata": e.metadata_json if include_payload else None,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "processed_at": e.processed_at.isoformat() if e.processed_at else None,
    }


@router.post("/outbox/{event_id}/requeue")
async def admin_outbox_requeue(
    event_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    stmt = select(OutboxEvent).where(OutboxEvent.id == event_id)
    result = await db.execute(stmt)
    e = result.scalars().first()
    if not e:
        raise OutboxEventNotFoundError(event_id)
    if e.status != "FAILED":
        raise OutboxRequeueInvalidStatusError()
    await db.execute(
        update(OutboxEvent)
        .where(OutboxEvent.id == event_id)
        .values(
            status="PENDING",
            last_error=None,
            processed_at=None,
        ),
    )
    await audit_repo.record(
        db,
        actor_user_id=current_user.user_id,
        action="outbox_requeue",
        resource_type="outbox_event",
        resource_id=str(event_id),
        metadata={"status": "PENDING"},
        ip_address=_client_ip(request),
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
        raise RideNotFoundError(ride_id)
    status_val = getattr(r.status, "value", None) or str(r.status)
    return {
        "ride_id": str(r.ride_id),
        "driver_id": str(r.driver_id),
        "group_id": str(r.group_id) if r.group_id else None,
        "origin_name": r.origin_name,
        "destination_name": r.destination_name,
        "departure_time": r.departure_time.isoformat() if r.departure_time else None,
        "estimated_arrival_time": r.estimated_arrival_time.isoformat() if r.estimated_arrival_time else None,
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
        raise BookingNotFoundError(booking_id)
    status_val = getattr(b.status, "value", None) or str(b.status)
    return {
        "booking_id": str(b.booking_id),
        "ride_id": str(b.ride_id),
        "passenger_id": str(b.passenger_id),
        "request_id": str(b.request_id) if b.request_id else None,
        "num_seats": b.num_seats,
        "pickup_name": b.pickup_name,
        "pickup_time": b.pickup_time.isoformat() if b.pickup_time else None,
        "status": status_val,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


@router.get("/system/overview")
async def admin_system_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.ops.read")
    health = await check_health()
    outbox_pending = int((await db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "PENDING"))) or 0)
    outbox_failed = int((await db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "FAILED"))) or 0)
    payments_pending = int((await db.scalar(select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PENDING))) or 0)
    payments_failed = int((await db.scalar(select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.FAILED))) or 0)
    return {
        "health": health,
        "outbox": {"pending": outbox_pending, "failed": outbox_failed},
        "billing": {"pending": payments_pending, "failed": payments_failed},
        "rabbitmq_clients": {
            "api": rabbit_client.is_connected(),
            "worker": worker_rabbit_client.is_connected(),
            "outbox": outbox_rabbit_client.is_connected(),
        },
    }


@router.get("/queues")
async def admin_queues(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.ops.read")
    outbox_pending = int((await db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "PENDING"))) or 0)
    outbox_failed = int((await db.scalar(select(func.count()).select_from(OutboxEvent).where(OutboxEvent.status == "FAILED"))) or 0)
    queues = []
    for queue_name, spec in QUEUE_SPECS.items():
        queues.append(
            {
                "queue_name": queue_name,
                "exchange_names": list(spec.exchange_names),
                "retry_enabled": spec.retry_enabled,
                "retry_delay_ms": spec.retry_delay_ms,
                "max_retries": spec.max_retries,
                "prefetch_count": spec.prefetch_count,
                "durable": spec.durable,
            },
        )
    return {
        "queues": queues,
        "outbox_depth": {"pending": outbox_pending, "failed": outbox_failed},
    }


@router.get("/workers")
async def admin_workers(
    current_user: User = Depends(get_current_admin_user),
):
    _require_capability(current_user, "admin.ops.read")
    return {
        "workers": [
            {
                "name": "notification-worker",
                "metrics_port": 9091,
                "rabbitmq_client_connected": worker_rabbit_client.is_connected(),
            },
            {
                "name": "task-worker",
                "metrics_port": 9092,
                "rabbitmq_client_connected": worker_rabbit_client.is_connected(),
            },
            {
                "name": "ai-worker",
                "metrics_port": 9093,
                "rabbitmq_client_connected": worker_rabbit_client.is_connected(),
            },
        ],
    }
