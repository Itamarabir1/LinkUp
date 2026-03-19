from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime,
    func,
    UniqueConstraint,
    Boolean,
    text,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, UUID as PG_UUID
from geoalchemy2 import Geography
import uuid
from app.db.base import Base
from app.domain.bookings.enum import BookingStatus
from sqlalchemy import Index


class BookingStatusEnumType(PG_ENUM):
    """PG_ENUM for booking_status: DB may return value ('cancelled') or name ('CANCELLED'); support both."""

    def _object_value_for_elem(self, elem):
        try:
            return self._object_lookup[elem]
        except KeyError:
            pass
        try:
            return BookingStatus(elem)
        except ValueError:
            pass
        try:
            return BookingStatus[elem]
        except KeyError:
            raise LookupError(
                f"'{elem}' is not among the defined enum values. Enum name: booking_status."
            ) from None


class Booking(Base):
    """
    Booking Entity - Senior Edition.
    הצומת (Junction) שמחברת בין נהג (דרך Ride) לבין נוסע (User).
    """

    __tablename__ = "bookings"

    booking_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 1. הקשר לנסיעה
    ride_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("rides.ride_id", ondelete="CASCADE"), nullable=False
    )

    # 2. הקשר הישיר לנוסע (התיקון הקריטי!)
    # ב-SQL שלך העמודה הזו קיימת, עכשיו היא קיימת גם כאן
    passenger_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )

    # 3. הקשר לבקשה המקורית (אופציונלי - ON DELETE SET NULL)
    request_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("passenger_requests.request_id", ondelete="SET NULL"),
        nullable=True,
    )

    # נתונים נוספים מה-SQL שלך
    num_seats = Column(Integer, nullable=False, default=1)
    pickup_name = Column(String(255))
    pickup_point = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    pickup_time = Column(DateTime(timezone=True), nullable=True)

    # ניהול תזכורות (Celery)
    reminder_sent = Column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # BookingStatusEnumType: result accepts both value and name from DB
    status = Column(
        BookingStatusEnumType(
            BookingStatus,
            name="booking_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=BookingStatus.PENDING,
        server_default=text("'pending_approval'"),
        index=True,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships (החיבורים שמונעים KeyError) ---

    # מתחבר ל-Ride.bookings
    ride = relationship("Ride", back_populates="bookings")

    # מתחבר ל-User.bookings (הקשר שחיפשת!)
    passenger = relationship("User", back_populates="bookings")

    # מתחבר ל-PassengerRequest.bookings
    passenger_request = relationship("PassengerRequest", back_populates="bookings")

    @property
    def passenger_name(self) -> str | None:
        """שם הנוסע – למייל, להזמנות שלי ולבוקינג. מקור: passenger_request.user או passenger."""
        if self.passenger_request and getattr(self.passenger_request, "user", None):
            u = self.passenger_request.user
            name = getattr(u, "full_name", None) or getattr(u, "first_name", None)
            if name and str(name).strip():
                return str(name).strip()
        if self.passenger:
            name = getattr(self.passenger, "full_name", None) or getattr(
                self.passenger, "first_name", None
            )
            if name and str(name).strip():
                return str(name).strip()
        return None

    __table_args__ = (
        # הבטחת שלמות נתונים: נוסע לא יכול להזמין מקום פעמיים באותה נסיעה
        UniqueConstraint("ride_id", "passenger_id", name="unique_passenger_per_ride"),
        Index("idx_bookings_ride", "ride_id"),
        Index("idx_bookings_passenger", "passenger_id"),
    )

    def __repr__(self):
        return f"<Booking(id={self.booking_id}, ride={self.ride_id}, passenger={self.passenger_id}, status={self.status})>"
