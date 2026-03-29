import uuid
from sqlalchemy import Column, String, Integer, DateTime, Text, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.db.base import Base

# ייבוא מהקבצים החדשים שפיצלת - זה מה שמונע כפילויות!


class OutboxEvent(Base):
    """
    ישות ה-Outbox במסד הנתונים.
    מייצגת אך ורק את הטבלה הפיזית.
    """

    __tablename__ = "outbox_events"

    # מזהה ייחודי
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # שם האירוע
    event_name = Column(String(100), nullable=False, index=True)

    # הנתונים עצמם
    payload = Column(JSONB, nullable=False)

    # רשימת היעדים (כאן נשמור את ה-value של ה-Enum בתור String)
    targets = Column(ARRAY(String), nullable=False)

    # מידע נוסף
    metadata_json = Column("metadata", JSONB, nullable=True)

    # ניהול סטטוס
    status = Column(String(20), default="PENDING", nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    # חותמות זמן
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("idx_outbox_pending", "created_at", postgresql_where=(status == "PENDING")),)

    def __repr__(self):
        return f"<OutboxEvent(name={self.event_name}, status={self.status}, id={self.id})>"
