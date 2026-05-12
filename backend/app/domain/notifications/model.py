"""NotificationRead — server-side read-state for the derived notifications feed."""

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func

from app.db.base import Base


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    booking_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("bookings.booking_id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at = Column(DateTime(timezone=True), primary_key=True)
    read_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
