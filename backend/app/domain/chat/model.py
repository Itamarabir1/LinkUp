"""
מודל צ'אט 1:1 – שיחה בין שני משתמשים בלבד.
Conversation = זוג משתמשים (מזוהה יחיד). Message = הודעה בשיחה.
"""

import uuid
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    ForeignKey,
    DateTime,
    Text,
    func,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base import Base


class Conversation(Base):
    """
    שיחת 1:1 בין שני משתמשים.
    user_id_1 < user_id_2 תמיד – כך הזוג ייחודי בלי כפילות (א־ב = ב־א).
    """

    __tablename__ = "conversations"

    conversation_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id_1 = Column(
        PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    user_id_2 = Column(
        PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id_1", "user_id_2", name="uq_conversation_pair"),
        CheckConstraint("user_id_1 < user_id_2", name="ck_conversation_ordered"),
    )

    user_1 = relationship("User", foreign_keys=[user_id_1])
    user_2 = relationship("User", foreign_keys=[user_id_2])
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self):
        return f"<Conversation(id={self.conversation_id}, users=({self.user_id_1},{self.user_id_2}))>"


class Message(Base):
    """הודעה אחת בתוך שיחת 1:1."""

    __tablename__ = "messages"

    message_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    body = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<Message(id={self.message_id}, conv={self.conversation_id}, sender={self.sender_id})>"


class ConversationParticipant(Base):
    """
    משתתף בשיחה (conversation).

    נשמר כשורה לכל (conversation_id, user_id) ומאפשר last_read_at לכל משתמש.
    מוכן להרחבה לקבוצות בעתיד.
    """

    __tablename__ = "conversation_participants"

    conversation_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_read_at = Column(DateTime(timezone=True), nullable=True)

    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ConversationParticipant(conv={self.conversation_id}, user={self.user_id})>"


class ChatAnalysis(Base):
    """ניתוח AI של שיחת צ'אט."""

    __tablename__ = "chat_analysis"

    analysis_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    driver_name = Column(Text)
    passenger_name = Column(Text)
    pickup_location = Column(Text)
    meeting_time = Column(Text)
    summary_hebrew = Column(Text)
    analysis_json = Column(JSON)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation = relationship("Conversation", foreign_keys=[conversation_id])

    def __repr__(self):
        return f"<ChatAnalysis(conv={self.conversation_id}, driver={self.driver_name}, passenger={self.passenger_name})>"
