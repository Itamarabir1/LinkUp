import uuid

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from app.db.base import Base

# Split enum module avoids circular imports


class OutboxEvent(Base):
    """
    ORM mapping for outbox_events table.
    """

    __tablename__ = "outbox_events"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Event name
    event_name = Column(String(100), nullable=False, index=True)

    # JSON payload
    payload = Column(JSONB, nullable=False)

    # Dispatch targets (enum values as strings)
    targets = Column(ARRAY(String), nullable=False)

    # Extra metadata
    metadata_json = Column("metadata", JSONB, nullable=True)

    # Processing state
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("idx_outbox_pending", "created_at", postgresql_where=(status == "PENDING")),)

    def __repr__(self):
        return f"<OutboxEvent(name={self.event_name}, status={self.status}, id={self.id})>"
