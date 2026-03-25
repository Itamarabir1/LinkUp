import uuid
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, inspect as sa_inspect
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.base import Base
from geoalchemy2 import Geography  # שימוש ב-Geography עבור PostGIS


class User(Base):
    """
    User Entity - Senior Edition.
    הישות המרכזית במערכת. משתמש יכול להיות נהג, נוסע או שניהם.
    """

    __tablename__ = "users"

    # מזהה ייחודי
    user_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)

    # אימות וניהול חשבון
    is_verified = Column(Boolean, default=False, nullable=False, server_default="false")
    google_id = Column(String(255), nullable=True)  # Google OAuth 'sub' – קישור חשבון קיים ל-Google
    is_active = Column(Boolean, default=True, server_default="true")
    is_admin = Column(Boolean, default=False, server_default="false")

    # פרופיל — מפתח S3 בלבד (prefix תיקייה), למשל avatars/{user_id}/. URLs מלאים נבנים ב-runtime.
    avatar_key = Column(String(255), nullable=True)
    fcm_token = Column(Text, nullable=True)
    # Refresh Token (ארוך תוקף) – נשמר ב-DB כדי לאפשר ביטול (logout מכל המכשירים)
    refresh_token = Column(Text, nullable=True)

    # מיקום אחרון (PostGIS Geography) - לחישובי מרחק במטרים
    last_location = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)

    # זמנים (Best Practice: שימוש ב-UTC)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # --- Relationships (The "Glue" of the System) ---

    # 1. נסיעות שהמשתמש יצר (כנהג)
    # מתחבר ל-Ride.driver
    rides_as_driver = relationship(
        "Ride",
        back_populates="driver",
        cascade="all, delete-orphan",
        passive_deletes=True,  # אופטימיזציה לביצועי מחיקה ב-DB
    )

    # 2. בקשות חיפוש (כנוסע מחפש / סוכן חכם)
    # מתחבר ל-PassengerRequest.user
    passenger_requests = relationship(
        "PassengerRequest",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 3. הזמנות מאושרות (כנוסע רשום בנסיעה)
    # מתחבר ל-Booking.passenger
    bookings = relationship(
        "Booking",
        back_populates="passenger",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 4. קבוצות שהמשתמש מנהל
    owned_groups = relationship("Group", back_populates="admin")
    # 5. חברויות בקבוצות
    group_memberships = relationship("GroupMember", back_populates="user")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, full_name='{self.full_name}', phone='{self.phone_number}')>"

    # --- Senior Helpers ---

    @property
    def is_driver(self) -> bool:
        """האם יש למשתמש נסיעות כנהג. בלי lazy load אם ה-relationship לא נטען."""
        try:
            if "rides_as_driver" not in sa_inspect(self).unloaded:
                rides = self.__dict__.get("rides_as_driver")
                return bool(rides)
        except Exception:
            pass
        return False

    @property
    def active_bookings_count(self) -> int:
        """ספירת הזמנות שאינן cancelled/rejected — רק אם bookings נטען בזיכרון."""
        try:
            if "bookings" not in sa_inspect(self).unloaded:
                bookings = self.__dict__.get("bookings", [])
                return sum(
                    1
                    for b in bookings
                    if (
                        getattr(getattr(b, "status", None), "value", b.status)
                        not in ("cancelled", "rejected")
                    )
                )
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

    # בתוך class User במודל שלך
