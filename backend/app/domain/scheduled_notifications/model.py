"""
ScheduledNotification — scheduled reminder row.

Replaces reminder_sent flags on rides and bookings.
Written by outbox worker after ride.created / booking.approved_by_driver.
Scanned by reminder_scheduler every 5 minutes — small efficient query thanks to partial index.
"""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.db.base import Base


class ScheduledNotificationType:
    PASSENGER_REMINDER = "passenger_reminder"
    DRIVER_REMINDER = "driver_reminder"


class ScheduledNotification(Base):
    __tablename__ = "scheduled_notifications"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Optional ride context (driver + passenger reminders)
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

    # Scheduled fire time (e.g. 30 min before departure)
    deliver_at = Column(DateTime(timezone=True), nullable=False)

    # NULL until successfully sent
    sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<ScheduledNotification(id={self.id}, type={self.type}, user_id={self.user_id}, deliver_at={self.deliver_at}, sent_at={self.sent_at})>"
        )
