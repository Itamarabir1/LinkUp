import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

# --- Imports ---
# ---------------------------
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride

logger = logging.getLogger(__name__)


class CRUDRide:
    """
    Database access for Ride entities (PostgreSQL).
    Uses flush() so the service layer owns transaction boundaries.
    """

    @staticmethod
    def _base_ride_stmt() -> Select:
        """
        Canonical select for rides shown in API responses.
        Ensures group and driver are eager-loaded (avoids MissingGreenlet).
        """
        return select(Ride).options(
            selectinload(Ride.group),
            selectinload(Ride.driver),
        )

    def create(self, db: Session, *, obj_in: dict[str, Any]) -> Ride:
        """
        Persist a ride from a mapper-built dict (geometries already resolved).
        """
        # 1. ORM from dict (geometries already materialized)
        db_obj = Ride(**obj_in)

        # 2. Persist
        db.add(db_obj)

        # flush() assigns DB id; commit happens in service (e.g. with db.begin())
        db.flush()

        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, ride_id: UUID) -> Ride | None:
        """Load by primary key (sync Session)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        return db.query(Ride).filter(Ride.ride_id == rid).first()

    async def get_async(self, db: AsyncSession, ride_id: UUID) -> Ride | None:
        """Load by primary key for AsyncSession (read_ride and async API)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = self._base_ride_stmt().where(Ride.ride_id == rid)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_with_driver(self, db: AsyncSession, ride_id: UUID) -> Ride | None:
        """Load ride with driver joined (passenger driver-info endpoint)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Ride).options(joinedload(Ride.driver)).where(Ride.ride_id == rid)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_for_update(self, db: AsyncSession, ride_id: UUID, driver_id: UUID | None = None) -> Ride | None:
        """
        Load ride with SELECT FOR UPDATE.

        When driver_id is set, ownership is enforced in the query.
        Row lock lasts until commit/rollback to reduce concurrent update races.
        """
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Ride).where(Ride.ride_id == rid)
        if driver_id is not None:
            did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
            stmt = stmt.where(Ride.driver_id == did)
        stmt = stmt.with_for_update()
        result = await db.execute(stmt)
        return result.scalars().first()

    def get_all(self, db: Session, status: RideStatus | None = None) -> list[Ride]:
        """List rides, optionally filtered by status (sync)."""
        query = db.query(Ride)
        if status:
            query = query.filter(Ride.status == status)
        return query.all()

    async def get_by_driver_id(
        self,
        db: AsyncSession,
        driver_id: UUID,
        status: RideStatus | None = None,
        limit: int = 20,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Ride]:
        """Keyset-paginated rides for a driver ordered by departure_time DESC, ride_id DESC."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        stmt = self._base_ride_stmt().where(Ride.driver_id == did)
        if status is not None:
            stmt = stmt.where(Ride.status == status)
        if after is not None:
            cursor_time, cursor_ride_id = after
            stmt = stmt.where(
                or_(
                    Ride.departure_time < cursor_time,
                    and_(
                        Ride.departure_time == cursor_time,
                        Ride.ride_id < cursor_ride_id,
                    ),
                )
            )
        stmt = stmt.order_by(Ride.departure_time.desc(), Ride.ride_id.desc())
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_group_id(
        self,
        db: AsyncSession,
        group_id: UUID,
        exclude_cancelled: bool = True,
        limit: int = 20,
        after: tuple[datetime, UUID] | None = None,
    ) -> list[Ride]:
        """Keyset-paginated rides for a group ordered by departure_time DESC, ride_id DESC."""
        gid = UUID(str(group_id)) if isinstance(group_id, str) else group_id
        stmt = self._base_ride_stmt().where(Ride.group_id == gid)
        if exclude_cancelled:
            stmt = stmt.where(Ride.status != RideStatus.CANCELLED)
        if after is not None:
            cursor_time, cursor_ride_id = after
            stmt = stmt.where(
                or_(
                    Ride.departure_time < cursor_time,
                    and_(
                        Ride.departure_time == cursor_time,
                        Ride.ride_id < cursor_ride_id,
                    ),
                )
            )
        stmt = stmt.order_by(Ride.departure_time.desc(), Ride.ride_id.desc())
        stmt = stmt.limit(limit + 1)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, db: AsyncSession, ride_id: UUID, status: RideStatus) -> Ride | None:
        """Update ride status under row lock."""
        ride = await self.get_for_update(db, ride_id)
        if ride:
            ride.status = status
            await db.flush()
        return ride

    def update_seats(self, db: Session, ride_id: UUID, num_seats_change: int) -> Ride | None:
        """Adjust available seats with consistency checks (sync)."""
        ride = self.get_for_update(db, ride_id)
        if ride:
            if ride.available_seats - num_seats_change < 0:
                raise ValueError("אין מספיק מושבים פנויים")

            ride.available_seats -= num_seats_change
            db.flush()
        return ride

    ALLOWED_UPDATE_FIELDS = ("available_seats", "departure_time")

    async def update_partial(self, db: AsyncSession, ride_id: UUID, driver_id: UUID, **updates: Any) -> Ride | None:
        """Partial update: available_seats and/or departure_time; ownership and seat rules enforced."""
        ride = await self.get_for_update(db, ride_id, driver_id)
        if not ride:
            return None

        # Avoid lazy-load (MissingGreenlet) in async context
        await db.refresh(ride, attribute_names=["bookings"])

        for key, value in updates.items():
            if key not in self.ALLOWED_UPDATE_FIELDS or value is None:
                continue
            if key == "available_seats":
                occupied = sum(b.num_seats for b in ride.bookings if getattr(b, "status", None) not in ("cancelled", "rejected"))
                if value < occupied:
                    raise ValueError(f"מספר מושבים לא יכול להיות קטן ממספר התפוסים ({occupied})")
                ride.available_seats = value
            elif key == "departure_time":
                ride.departure_time = value
                if ride.duration_min is not None:
                    mins = int(ride.duration_min) if ride.duration_min else 0
                    ride.estimated_arrival_time = value + timedelta(minutes=mins)
        await db.flush()
        await db.refresh(ride)
        return ride

    async def get_for_notification(self, db: AsyncSession, ride_id: UUID) -> Ride | None:
        """Load ride with driver/group for notification context."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = self._base_ride_stmt().where(Ride.ride_id == rid)
        result = await db.execute(stmt)
        return result.scalars().first()


# Singleton for app-wide use
crud_ride = CRUDRide()
