import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Group(Base):
    __tablename__ = "groups"

    group_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    invite_code = Column(String(64), unique=True, nullable=False, index=True)
    admin_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    max_members = Column(Integer, nullable=True)
    invite_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Group image S3 key, e.g. GROUPS/<group_id>/image.webp
    avatar_key = Column(String(255), nullable=True)
    # Group description up to 500 chars (admin-edited)
    description = Column(String(500), nullable=True)

    admin = relationship("User", back_populates="owned_groups", foreign_keys=[admin_id])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Group(group_id={self.group_id}, name='{self.name}', admin_id={self.admin_id})>"


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("groups.group_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), default="member", nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    def __repr__(self):
        return f"<GroupMember(id={self.id}, group_id={self.group_id}, user_id={self.user_id}, role='{self.role}')>"
