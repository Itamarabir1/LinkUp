"""
ScheduledNotification — רשומת תזכורת מתוזמנת.

מחליפה את reminder_sent flag על rides ו-bookings.
נכתבת ע"י outbox worker אחרי ride.created / booking.approved_by_driver.
נסרקת ע"י reminder_scheduler כל 5 דקות — query קטן ויעיל בזכות partial index.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db.base import Base


class ScheduledNotificationType:
    PASSENGER_REMINDER = "passenger_reminder"
    DRIVER_REMINDER = "driver_reminder"


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ride_id אופציונלי — נשלח גם לנוסע וגם לנהג
    ride_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("rides.ride_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 'passenger_reminder' | 'driver_reminder'
    type = Column(String(50), nullable=False)

    # מתי לשלוח — 30 דקות לפני departure_time
    deliver_at = Column(DateTime(timezone=True), nullable=False)

    # מתי נשלח בפועל — NULL = טרם נשלח
    sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ScheduledNotification(id={self.id}, type={self.type}, "
            f"user_id={self.user_id}, deliver_at={self.deliver_at}, sent_at={self.sent_at})>"
        )
