import uuid

from geoalchemy2 import Geography  # PostGIS geography type
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """
    User entity — core domain object; can act as driver, passenger, or both.
    """

    __tablename__ = "users"

    # Primary key
    user_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # Verification & account flags
    is_verified = Column(Boolean, default=False, nullable=False, server_default="false")
    google_id = Column(String(255), nullable=True)  # Google OAuth `sub` — link existing account
    is_active = Column(Boolean, default=True, server_default="true")
    is_admin = Column(Boolean, default=False, server_default="false")

    # Profile media — S3 key prefix only (e.g. avatars/{user_id}/); URLs built at runtime.
    avatar_key = Column(String(255), nullable=True)
    avatar_staging_key = Column(String(255), nullable=True)
    avatar_status = Column(String(20), nullable=False, server_default="none", default="none")
    fcm_token = Column(Text, nullable=True)
    # Long-lived refresh token — stored in DB for revoke-all (logout)
    refresh_token = Column(Text, nullable=True)

    # Last known location (PostGIS geography) — distance queries in meters
    last_location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)

    # Timestamps (store in UTC)
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships (The "Glue" of the System) ---

    # 1. Rides created as driver → Ride.driver
    rides_as_driver = relationship(
        "Ride",
        back_populates="driver",
        cascade="all, delete-orphan",
        passive_deletes=True,  # DB-level delete performance
    )

    # 2. Passenger search requests → PassengerRequest.user
    passenger_requests = relationship(
        "PassengerRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 3. Bookings as passenger → Booking.passenger
    bookings = relationship(
        "Booking",
        back_populates="passenger",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 4. Groups this user admins
    owned_groups = relationship("Group", back_populates="admin")
    # 5. Group memberships
    group_memberships = relationship("GroupMember", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, full_name='{self.full_name}', phone='{self.phone_number}')>"

    # --- Senior Helpers ---

    @property
    def is_driver(self) -> bool:
        """True if user has driver rides loaded (avoids lazy load if unloaded)."""
        try:
            if "rides_as_driver" not in sa_inspect(self).unloaded:
                rides = self.__dict__.get("rides_as_driver")
                return bool(rides)
        except Exception:
            pass
        return False

    @property
    def active_bookings_count(self) -> int:
        """Count non-cancelled/rejected bookings when relationship is loaded."""
        try:
            if "bookings" not in sa_inspect(self).unloaded:
                bookings = self.__dict__.get("bookings", [])
                return sum(1 for b in bookings if (getattr(getattr(b, "status", None), "value", b.status) not in ("cancelled", "rejected")))
        except Exception:
            pass
        return 0

    def to_event_payload(self) -> dict:
        """
        מרכז את הלוגיקה של 'איזה נתונים יוצאים החוצה'.
        עכשיו השדות יזוהו כי הפונקציה מוזחת (Tab) פנימה לתוך ה-Class.
        """
        return {
            "user_id": self.user_id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_verified": self.is_verified,
        }
