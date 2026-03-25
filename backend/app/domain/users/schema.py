from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, computed_field
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.utils.validators import (
    normalize_email_for_auth,
    validate_password_strength,
    validate_phone_number,
)
from app.core.exceptions.auth import PasswordTooWeakError
from app.core.exceptions.validation import InvalidEmailError, InvalidPhoneError


class UserBaseSchema(BaseModel):
    """
    סכימת בסיס עם וולידציות משותפות – משתמש ב-core.utils.validators (מקור אמת יחיד).
    """

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]):
        if v is None:
            return v
        try:
            return normalize_email_for_auth(v)
        except ValueError as e:
            raise InvalidEmailError(email=v) from e

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]):
        if v is None:
            return v
        try:
            return validate_phone_number(v)
        except ValueError as e:
            raise InvalidPhoneError(phone=v) from e

    @field_validator("password", "new_password", check_fields=False)
    @classmethod
    def validate_password_strength(cls, v: Optional[str]):
        if v is None:
            return v
        try:
            return validate_password_strength(v)
        except ValueError:
            raise PasswordTooWeakError()


# --- קריאה (Response) ---
def _avatar_url_from_key(avatar_key: Optional[str], filename: str) -> Optional[str]:
    """בונה URL מלא ל-S3. אם avatar_key הוא staging (avatars/staging/...) — מחזיר את ה-key כקובץ יחיד."""
    if not avatar_key or not settings.S3_BUCKET_NAME:
        return None
    base = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
    if avatar_key.startswith("avatars/staging/"):
        return f"{base}{avatar_key}"
    return f"{base}{avatar_key}{filename}"


class UserRead(BaseModel):
    user_id: UUID
    full_name: str
    phone_number: str
    email: Optional[EmailStr] = None
    avatar_key: Optional[str] = None
    is_verified: bool = False
    is_admin: bool = False

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url_small(self) -> Optional[str]:
        """150x150 — רשימות צ'אט, אווטארים קטנים."""
        return _avatar_url_from_key(self.avatar_key, "150x150.webp")

    @computed_field
    @property
    def avatar_url_medium(self) -> Optional[str]:
        """400x400 — תמונת פרופיל ראשית."""
        return _avatar_url_from_key(self.avatar_key, "400x400.webp")


# app/domain/users/schema.py


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(
        ..., pattern=r"^\+?[1-9]\d{1,14}$"
    )  # וולידציה לטלפון בינלאומי
    password: str = Field(..., min_length=8)  # הסיסמה הגולמית מהמשתמש
    email: Optional[EmailStr] = None
    fcm_token: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- עדכונים ---
class UserUpdate(UserBaseSchema):
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None


# --- מיקום ו-FCM ---
class UserLocationUpdate(BaseModel):
    # וולידציה גיאוגרפית כבר ברמת הסכמה - מעולה!
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FCMTokenUpdate(BaseModel):
    fcm_token: str = Field(..., min_length=10)


# --- תגובות גנריות ---
class MessageResponse(BaseModel):
    message: str
    status: str = "success"
    model_config = ConfigDict(from_attributes=True)


class UserAvatarResponse(BaseModel):
    """תגובה לאחר העלאת אווטאר – מחזיר מפתח או URL לפי צורך."""

    avatar_key: Optional[str] = None
    avatar_url_medium: Optional[str] = None


class AvatarUploadAcceptedResponse(BaseModel):
    """תגובה ל-202 – העלאת אווטאר התקבלה ועתידה לעבור עיבוד ברקע."""

    message: str = "Avatar upload accepted"
    status: str = "accepted"


class AvatarUploadUrlRequest(BaseModel):
    """בקשה ל-presigned URL להעלאת אווטאר."""

    filename: Optional[str] = Field(
        None, description="שם הקובץ (אופציונלי, לזיהוי סיומת)"
    )


class AvatarUploadUrlResponse(BaseModel):
    """תגובה עם presigned URL להעלאת אווטאר."""

    upload_url: str = Field(..., description="Presigned URL להעלאה ישירה ל-S3")
    staging_key: str = Field(..., description="מפתח staging לשימוש באישור העלאה")
    expires_in: int = Field(300, description="זמן תוקף URL בשניות")


class AvatarUploadConfirmRequest(BaseModel):
    """אישור העלאה לאחר שהלקוח העלה ישירות ל-S3."""

    staging_key: str = Field(..., description="מפתח staging שקיבל ב-upload_url")
