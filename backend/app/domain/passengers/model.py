from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    text,
    Numeric,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID
from geoalchemy2 import Geography  # שימוש ב-Geography לסנכרון עם ה-SQL
import uuid
from app.db.base import Base
from app.domain.passengers.enum import PassengerStatus


class PassengerStatusEnumType(PG_ENUM):
    """PG_ENUM for passenger_request_status: DB may return value or name; support both."""

    def _object_value_for_elem(self, elem):
        try:
            return self._object_lookup[elem]
        except KeyError:
            pass
        try:
            return PassengerStatus(elem)
        except ValueError:
            pass
        try:
            return PassengerStatus[elem]
        except KeyError:
            raise LookupError(f"'{elem}' is not among the defined enum values. Enum name: passenger_request_status.") from None


class PassengerRequest(Base):
    """
    PassengerRequest Entity - Senior Edition.
    מייצג את ה"סוכן החכם" של הנוסע שמחפש נסיעה.
    """

    __tablename__ = "passenger_requests"

    request_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FK למשתמש הפיזי
    passenger_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    group_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("groups.group_id", ondelete="SET NULL"),
        nullable=True,
    )

    # נתונים פיזיים
    num_passengers = Column(Integer, nullable=False, default=1)
    is_auto_generated = Column(Boolean, default=False, server_default="false")
    is_notification_active = Column(Boolean, default=True, server_default="true")

    # PostGIS - Geography לחישובי מרחק במטרים
    pickup_name = Column(String(255))
    pickup_geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination_name = Column(String(255))
    destination_geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)

    requested_departure_time = Column(DateTime(timezone=True), nullable=False)
    # התאמה לשם העמודה ב-SQL: search_radius_meters
    search_radius_meters = Column(Integer, default=500)

    # נתונים נוספים מה-SQL
    distance_km = Column(Numeric(10, 2), default=0)
    duration_min = Column(Numeric(10, 2), default=0)

    # PassengerStatusEnumType: result accepts both value and name from DB
    status = Column(
        PassengerStatusEnumType(
            PassengerStatus,
            name="passenger_request_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PassengerStatus.ACTIVE,
        server_default=text("'active'"),
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_passenger_status_time", "status", "requested_departure_time"),
        Index("idx_passenger_pickup_gist", "pickup_geom", postgresql_using="gist"),
        Index("idx_passenger_dest_gist", "destination_geom", postgresql_using="gist"),
    )

    # --- Relationships ---

    # מקשר חזרה ל-User.passenger_requests
    user = relationship("User", back_populates="passenger_requests")
    group = relationship("Group")

    # מקשר לבוקינגס שנוצרו מהבקשה הזו
    bookings = relationship("Booking", back_populates="passenger_request", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PassengerRequest(id={self.request_id}, user_id={self.passenger_id}, status={self.status})>"
