from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, computed_field

from sqlalchemy import inspect as sa_inspect

from app.core.config import settings


def _group_avatar_url(avatar_key: Optional[str]) -> Optional[str]:
    """בונה URL מלא לתמונת קבוצה מ-S3."""
    if not avatar_key or not settings.S3_BUCKET_NAME:
        return None
    base = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
    return f"{base}{avatar_key}"


class GroupCreate(BaseModel):
    name: str
    max_members: Optional[int] = None
    description: Optional[str] = None  # עד 500 תווים


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None  # עד 500 תווים, וולידציה ב-Field לא חובה כאן (מודל DB מגביל)


class GroupOut(BaseModel):
    group_id: UUID
    name: str
    invite_code: str
    admin_id: UUID
    is_active: bool
    max_members: Optional[int]
    invite_expires_at: Optional[datetime]
    created_at: datetime
    member_count: Optional[int] = None
    avatar_key: Optional[str] = None
    description: Optional[str] = None

    @computed_field
    @property
    def avatar_url(self) -> Optional[str]:
        return _group_avatar_url(self.avatar_key)

    class Config:
        from_attributes = True


def group_to_out(group: Any, member_count: Optional[int] = None) -> "GroupOut":
    """בניית GroupOut ממודל ORM — בלי group.__dict__."""
    return GroupOut(
        group_id=group.group_id,
        name=group.name,
        invite_code=group.invite_code,
        admin_id=group.admin_id,
        is_active=group.is_active,
        max_members=group.max_members,
        invite_expires_at=group.invite_expires_at,
        created_at=group.created_at,
        member_count=member_count,
        avatar_key=group.avatar_key,
        description=group.description,
    )


class GroupMemberOut(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def group_member_to_out(member: Any) -> GroupMemberOut:
    """שם מלא מ-user רק אם נטען — בלי lazy load."""
    full_name: Optional[str] = None
    try:
        st = sa_inspect(member)
        if "user" not in st.unloaded:
            u = member.__dict__.get("user")
            if u is not None:
                fn = getattr(u, "full_name", None)
                if fn and str(fn).strip():
                    full_name = str(fn).strip()
    except Exception:
        pass
    return GroupMemberOut(
        id=member.id,
        group_id=member.group_id,
        user_id=member.user_id,
        role=member.role,
        joined_at=member.joined_at,
        full_name=full_name,
    )


class GroupImageUploadResponse(BaseModel):
    upload_url: str
    key: str


class GroupImageConfirmRequest(BaseModel):
    key: str