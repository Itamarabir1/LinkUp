import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

# --- הייבואים שחסרים לך ---
# ---------------------------
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.rides.enum import RideStatus
from app.domain.rides.model import Ride

logger = logging.getLogger(__name__)


class CRUDRide:
    """
    אחריות: ניהול הגישה למסד הנתונים (PostgreSQL) עבור ישות הנסיעה.
    Senior Tip: שימוש ב-db.flush() מאפשר לסרוויס לנהל את ה-Transaction (Atomic).
    """

    @staticmethod
    def _base_ride_stmt() -> Select:
        """
        מקור אמת יחיד לטעינת Rides לתצוגה.
        כל query שמחזיר Rides ל-RideResponse חייב לעבור דרך כאן.
        מבטיח ש-group ו-driver תמיד נטענים — אין MissingGreenlet.
        """
        return select(Ride).options(
            selectinload(Ride.group),
            selectinload(Ride.driver),
        )

    def create(self, db: Session, *, obj_in: dict[str, Any]) -> Ride:
        """
        יצירת נסיעה - Clean Version:
        מקבל מילון מוכן (אחרי Mapper) ושומר אותו.
        """
        # 1. יצירת האובייקט ישירות מהמילון
        # המילון כבר מכיל origin_geom, destination_geom ו-route_coords כאובייקטים גיאומטריים
        db_obj = Ride(**obj_in)

        # 2. שמירה
        db.add(db_obj)

        # משתמשים ב-flush כדי שהאובייקט יקבל ID מבסיס הנתונים
        # אבל ה-commit עצמו יקרה בסרוויס (בתוך ה-with db.begin())
        db.flush()

        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, ride_id: UUID) -> Ride | None:
        """שליפה מהירה לפי מפתח ראשי (Session סינכרוני)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        return db.query(Ride).filter(Ride.ride_id == rid).first()

    async def get_async(self, db: AsyncSession, ride_id: UUID) -> Ride | None:
        """שליפה לפי מפתח ראשי ל-AsyncSession (לשימוש ב-read_ride ו-API אסינכרוני)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = self._base_ride_stmt().where(Ride.ride_id == rid)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_with_driver(self, db: AsyncSession, ride_id: UUID) -> Ride | None:
        """שליפת נסיעה עם טעינת הנהג (לפרטי נהג לתצוגה לנוסע)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = select(Ride).options(joinedload(Ride.driver)).where(Ride.ride_id == rid)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_for_update(self, db: AsyncSession, ride_id: UUID, driver_id: UUID | None = None) -> Ride | None:
        """
        Senior Implementation: שליפת נסיעה עם נעילת שורה (FOR UPDATE).

        - אם driver_id מסופק: האימות מתבצע ב-DB (מונע גישה למי שאינו הבעלים).
        - with_for_update(): נועל את השורה עד לסיום הטרנזקציה (Commit/Rollback),
          מה שמונע מ-Race Conditions לקרות (למשל: נהג ונוסע שמבטלים בו-זמנית).
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
        """שליפה עם פילטור לפי סטטוס"""
        query = db.query(Ride)
        if status:
            query = query.filter(Ride.status == status)
        return query.all()

    async def get_by_driver_id(
        self,
        db: AsyncSession,
        driver_id: UUID,
        status: RideStatus | None = None,
    ) -> list[Ride]:
        """שליפת נסיעות לפי נהג (למסך 'הנסיעות שלי')."""
        did = UUID(str(driver_id)) if isinstance(driver_id, str) else driver_id
        stmt = self._base_ride_stmt().where(Ride.driver_id == did)
        if status is not None:
            stmt = stmt.where(Ride.status == status)
        stmt = stmt.order_by(Ride.departure_time.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_group_id(
        self,
        db: AsyncSession,
        group_id: UUID,
        exclude_cancelled: bool = True,
    ) -> list[Ride]:
        """שליפת נסיעות לפי קבוצה (לטאב נסיעות במסך קבוצה)."""
        gid = UUID(str(group_id)) if isinstance(group_id, str) else group_id
        stmt = self._base_ride_stmt().where(Ride.group_id == gid)
        if exclude_cancelled:
            stmt = stmt.where(Ride.status != RideStatus.CANCELLED)
        stmt = stmt.order_by(Ride.departure_time.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, db: AsyncSession, ride_id: UUID, status: RideStatus) -> Ride | None:
        """עדכון סטטוס מאובטח (SELECT FOR UPDATE)"""
        ride = await self.get_for_update(db, ride_id)
        if ride:
            ride.status = status
            await db.flush()
        return ride

    def update_seats(self, db: Session, ride_id: UUID, num_seats_change: int) -> Ride | None:
        """עדכון מושבים אטומי עם בדיקת תקינות"""
        ride = self.get_for_update(db, ride_id)
        if ride:
            if ride.available_seats - num_seats_change < 0:
                raise ValueError("אין מספיק מושבים פנויים")

            ride.available_seats -= num_seats_change
            db.flush()
        return ride

    ALLOWED_UPDATE_FIELDS = ("available_seats", "departure_time")

    async def update_partial(self, db: AsyncSession, ride_id: UUID, driver_id: UUID, **updates: Any) -> Ride | None:
        """עדכון חלקי – רק available_seats ו-departure_time. בודק בעלות וולידציית מושבים."""
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
        """שליפת נסיעה עם נהג (לבניית קונטקסט במייל/פוש)."""
        rid = UUID(str(ride_id)) if isinstance(ride_id, str) else ride_id
        stmt = self._base_ride_stmt().where(Ride.ride_id == rid)
        result = await db.execute(stmt)
        return result.scalars().first()


# יצירת מופע יחיד (Singleton) לשימוש בכל האפליקציה
crud_ride = CRUDRide()
