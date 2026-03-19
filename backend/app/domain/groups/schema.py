from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, computed_field

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


class GroupMemberOut(BaseModel):
    id: UUID
    group_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime

    @computed_field
    @property
    def full_name(self) -> Optional[str]:
        user = getattr(self, "user", None)
        return getattr(user, "full_name", None) if user is not None else None

    class Config:
        from_attributes = True


class GroupImageUploadResponse(BaseModel):
    upload_url: str
    key: str


class GroupImageConfirmRequest(BaseModel):
    key: str