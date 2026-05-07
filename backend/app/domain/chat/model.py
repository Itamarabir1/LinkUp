"""
1:1 chat models — conversation between exactly two users.
Conversation = unique user pair. Message = one message in a conversation.
"""

import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Conversation(Base):
    """
    1:1 conversation between two users.
    user_id_1 < user_id_2 always — unique unordered pair (A–B equals B–A).
    """

    __tablename__ = "conversations"

    conversation_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id_1 = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    user_id_2 = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)

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
    """A single message inside a 1:1 conversation."""

    __tablename__ = "messages"

    message_id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("idx_messages_sender_id", "sender_id"),)

    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])

    def __repr__(self):
        return f"<Message(id={self.message_id}, conv={self.conversation_id}, sender={self.sender_id})>"


class ConversationParticipant(Base):
    """
    Participant in a conversation.

    One row per (conversation_id, user_id) with per-user last_read_at.
    Structured to allow future group chat expansion.
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
    last_read_message_id = Column(BigInteger, nullable=True)

    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ConversationParticipant(conv={self.conversation_id}, user={self.user_id})>"


class ChatAnalysis(Base):
    """Persisted AI analysis for a chat conversation."""

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
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation = relationship("Conversation", foreign_keys=[conversation_id])

    def __repr__(self):
        return f"<ChatAnalysis(conv={self.conversation_id}, driver={self.driver_name}, passenger={self.passenger_name})>"
