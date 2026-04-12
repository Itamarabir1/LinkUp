import uuid

from geoalchemy2 import Geography
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    inspect as sa_inspect,
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.domain.bookings.enum import BookingStatus


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
            raise LookupError(f"'{elem}' is not among the defined enum values. Enum name: booking_status.") from None


class Booking(Base):
    """
    Booking Entity - Senior Edition.
    הצומת (Junction) שמחברת בין נהג (דרך Ride) לבין נוסע (User).
    """

    __tablename__ = "bookings"

    booking_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # 1. Ride FK
    ride_id = Column(PG_UUID(as_uuid=True), ForeignKey("rides.ride_id", ondelete="CASCADE"), nullable=False)

    # 2. Passenger user FK
    passenger_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    # 3. Source passenger request (optional, ON DELETE SET NULL)
    request_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("passenger_requests.request_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Booking details
    num_seats = Column(Integer, nullable=False, default=1)
    pickup_name = Column(String(255))
    pickup_point = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    pickup_time = Column(DateTime(timezone=True), nullable=True)

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

    # --- Relationships ---

    # Ride.bookings
    ride = relationship("Ride", back_populates="bookings")

    # User.bookings
    passenger = relationship("User", back_populates="bookings")

    # PassengerRequest.bookings
    passenger_request = relationship("PassengerRequest", back_populates="bookings")

    @property
    def passenger_name(self) -> str | None:
        """
        Display name for passenger without async lazy loads.
        Priority: passenger_request.user, then passenger.
        """

        def _name_from_user(u) -> str | None:
            if not u:
                return None
            name = getattr(u, "full_name", None) or getattr(u, "first_name", None)
            if name and str(name).strip():
                return str(name).strip()
            return None

        try:
            st = sa_inspect(self)
            if "passenger_request" not in st.unloaded:
                pr = self.__dict__.get("passenger_request")
                if pr is not None:
                    pr_st = sa_inspect(pr)
                    if "user" not in pr_st.unloaded:
                        u = pr.__dict__.get("user")
                        n = _name_from_user(u)
                        if n:
                            return n
            if "passenger" not in st.unloaded:
                passenger = self.__dict__.get("passenger")
                n = _name_from_user(passenger)
                if n:
                    return n
        except Exception:
            pass
        return None

    __table_args__ = (
        # One booking per passenger per ride
        UniqueConstraint("ride_id", "passenger_id", name="unique_passenger_per_ride"),
        Index("idx_bookings_ride", "ride_id"),
        Index("idx_bookings_passenger", "passenger_id"),
    )

    def __repr__(self):
        return f"<Booking(id={self.booking_id}, ride={self.ride_id}, passenger={self.passenger_id}, status={self.status})>"
