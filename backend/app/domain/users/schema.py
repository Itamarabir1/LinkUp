from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.core.config import settings
from app.core.exceptions.auth import PasswordTooWeakError
from app.core.exceptions.validation import InvalidEmailError, InvalidPhoneError
from app.infrastructure.s3.service import storage_service
from app.core.utils.validators import (
    normalize_email_for_auth,
    validate_password_strength,
    validate_phone_number,
)


class UserBaseSchema(BaseModel):
    """
    סכימת בסיס עם וולידציות משותפות – משתמש ב-core.utils.validators (מקור אמת יחיד).
    """

    full_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    password: str | None = None
    new_password: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str | None):
        if v is None:
            return v
        try:
            return normalize_email_for_auth(v)
        except ValueError as e:
            raise InvalidEmailError(email=v) from e

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str | None):
        if v is None:
            return v
        try:
            return validate_phone_number(v)
        except ValueError as e:
            raise InvalidPhoneError(phone=v) from e

    @field_validator("password", "new_password", check_fields=False)
    @classmethod
    def validate_password_strength(cls, v: str | None):
        if v is None:
            return v
        try:
            return validate_password_strength(v)
        except ValueError:
            raise PasswordTooWeakError()


# --- קריאה (Response) ---
def _avatar_url_from_key(avatar_key: str | None, filename: str) -> str | None:
    """בונה presigned read URL ל-S3 (GET)."""
    if not avatar_key or not settings.S3_BUCKET_NAME:
        return None
    if avatar_key.startswith("avatars/staging/"):
        key = avatar_key
    else:
        key = f"{avatar_key}{filename}"
    try:
        return storage_service.generate_read_url(key)
    except Exception:
        # Best-effort: לא מפילים response בגלל בעיית חתימה רגעית.
        return None


class UserRead(BaseModel):
    user_id: UUID
    full_name: str
    phone_number: str
    email: EmailStr | None = None
    avatar_key: str | None = None
    avatar_status: str = "none"
    is_verified: bool = False
    is_admin: bool = False

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url_small(self) -> str | None:
        """150x150 — רשימות צ'אט, אווטארים קטנים."""
        return _avatar_url_from_key(self.avatar_key, "150x150.webp")

    @computed_field
    @property
    def avatar_url_medium(self) -> str | None:
        """400x400 — תמונת פרופיל ראשית."""
        return _avatar_url_from_key(self.avatar_key, "400x400.webp")


# app/domain/users/schema.py


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")  # וולידציה לטלפון בינלאומי
    password: str = Field(..., min_length=8)  # הסיסמה הגולמית מהמשתמש
    email: EmailStr | None = None
    fcm_token: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- עדכונים ---
class UserUpdate(UserBaseSchema):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None


# --- מיקום ו-FCM ---
class UserLocationUpdate(BaseModel):
    # וולידציה גיאוגרפית כבר ברמת הסכמה - מעולה!
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FCMTokenUpdate(BaseModel):
    fcm_token: str | None = Field(None)


# --- תגובות גנריות ---
class MessageResponse(BaseModel):
    message: str
    status: str = "success"
    model_config = ConfigDict(from_attributes=True)


class UserAvatarResponse(BaseModel):
    """תגובה לאחר העלאת אווטאר – מחזיר מפתח או URL לפי צורך."""

    avatar_key: str | None = None
    avatar_url_medium: str | None = None


class AvatarUploadAcceptedResponse(BaseModel):
    """תגובה ל-202 – העלאת אווטאר התקבלה ועתידה לעבור עיבוד ברקע."""

    message: str = "Avatar upload accepted"
    status: str = "accepted"


class AvatarUploadUrlRequest(BaseModel):
    """בקשה ל-presigned URL להעלאת אווטאר."""

    filename: str | None = Field(None, description="שם הקובץ (אופציונלי, לזיהוי סיומת)")


class AvatarUploadUrlResponse(BaseModel):
    """תגובה עם presigned URL להעלאת אווטאר."""

    upload_url: str = Field(..., description="Presigned URL להעלאה ישירה ל-S3")
    staging_key: str = Field(..., description="מפתח staging לשימוש באישור העלאה")
    expires_in: int = Field(300, description="זמן תוקף URL בשניות")


class AvatarUploadConfirmRequest(BaseModel):
    """אישור העלאה לאחר שהלקוח העלה ישירות ל-S3."""

    staging_key: str = Field(..., description="מפתח staging שקיבל ב-upload_url")
