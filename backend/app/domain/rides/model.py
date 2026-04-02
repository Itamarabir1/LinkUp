from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Numeric,
    Index,
    text,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID
from geoalchemy2 import Geography
import uuid

from app.db.base import Base
from app.domain.rides.enum import RideStatus
from app.domain.geo.utils import convert_db_route_to_list


def _ride_status_from_db(value):
    """Convert DB string (value or name) to RideStatus."""
    if value is None:
        return None
    try:
        return RideStatus(value)  # by value: 'open' -> OPEN
    except ValueError:
        pass
    try:
        return RideStatus[value]  # by name: 'OPEN' -> OPEN
    except KeyError:
        raise LookupError(f"'{value}' is not a valid ride_status.") from None


class RideStatusEnumType(TypeDecorator):
    """Wraps PG ride_status enum so result accepts both value ('open') and name ('OPEN') from DB."""

    impl = PG_ENUM(
        RideStatus,
        name="ride_status",
        create_type=False,
        values_callable=lambda x: [e.value for e in x],
    )
    cache_ok = True

    def process_result_value(self, value, dialect):
        return _ride_status_from_db(value)


class Ride(Base):
    """
    Ride Entity - Senior Edition.
    מייצג נסיעה שהוצעה ע"י נהג (User בתפקיד Driver).
    """

    __tablename__ = "rides"

    ride_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ה-FK שמחבר את הנסיעה ל-User הפיזי (הנהג)
    driver_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("groups.group_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # --- זמנים ---
    departure_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    estimated_arrival_time = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- מיקומים (PostGIS) ---
    origin_name = Column(String(255))
    destination_name = Column(String(255))
    origin_geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination_geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    route_coords = Column(Geography(geometry_type="LINESTRING", srid=4326), nullable=True)
    route_summary = Column(String(255), nullable=True)  # סיכום המסלול (כביש) מגוגל

    # --- נתונים פיזיים (מותאם ל-SQL שלך) ---
    distance_km = Column(Numeric(10, 2), nullable=True)
    duration_min = Column(Numeric(10, 2), nullable=True)

    # שים לב: שיניתי ל-available_seats כדי שיתאים לשם העמודה ב-SQL ששלחת
    available_seats = Column(Integer, nullable=False, default=4)

    price = Column(Numeric(10, 2), default=0.0)

    # --- סטטוס ---
    # RideStatusEnumType: result accepts both value ('open') and name ('OPEN') from DB
    status = Column(
        RideStatusEnumType(),
        nullable=False,
        default=RideStatus.OPEN,
        server_default=text("'open'"),
        index=True,
    )

    __table_args__ = (
        Index("idx_ride_route_gist", "route_coords", postgresql_using="gist"),
        Index("idx_ride_time_status", "departure_time", "status"),
    )

    # --- Relationships (Senior Standard) ---

    # הקשר ל-User: 'rides_as_driver' חייב להופיע ב-back_populates של מודל User
    driver = relationship("User", back_populates="rides_as_driver")
    group = relationship("Group")

    # הקשר ל-Bookings: כל המושבים שנתפסו בנסיעה הזו
    # (lazy=select – נטען רק בעת גישה, כדי ש-refresh אחרי יצירת נסיעה לא ייכשל
    # אם טבלת bookings עדיין לא קיימת)
    bookings = relationship(
        "Booking",
        back_populates="ride",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # --- Business Logic & Properties ---

    @property
    def total_capacity(self) -> int:
        """מחזיר את כמות המושבים המקורי שהנהג הציע"""
        return self.available_seats

    @property
    def occupied_seats(self) -> int:
        """מחשב כמה מושבים תפוסים בפועל על בסיס הזמנות מאושרות בלבד"""
        # אופטימיזציה: סכימת המושבים מתוך רשימת הבוקינגס בזיכרון
        return sum(b.num_seats for b in self.bookings if b.status not in ["cancelled", "rejected"])

    @property
    def seats_left(self) -> int:
        """כמה מושבים פנויים באמת נשארו לנסיעה זו"""
        return max(0, self.available_seats - self.occupied_seats)

    @property
    def is_full(self) -> bool:
        """האם הרכב מלא?"""
        return self.seats_left <= 0

    # --- Utilities ---

    @property
    def route_coords_list(self):
        """המרת קואורדינטות מה-DB לרשימת Python נוחה ל-Frontend"""
        return convert_db_route_to_list(self.route_coords)

    def can_be_cancelled(self) -> bool:
        """בדיקה האם ניתן לבטל את הנסיעה (לוגיקה עסקית)"""
        return self.status in [RideStatus.OPEN, RideStatus.FULL]

    def __repr__(self):
        return f"<Ride(id={self.ride_id}, driver_id={self.driver_id}, seats_left={self.seats_left})>"
