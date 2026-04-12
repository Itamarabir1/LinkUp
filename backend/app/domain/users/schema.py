from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

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


# --- Read (response) ---
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
        """150x150 — chat lists, small avatars."""
        return storage_service.build_avatar_url(self.avatar_key, "150x150.webp")

    @computed_field
    @property
    def avatar_url_medium(self) -> str | None:
        """400x400 — main profile image."""
        return storage_service.build_avatar_url(self.avatar_key, "400x400.webp")


# app/domain/users/schema.py


class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")  # E.164-style phone validation
    password: str = Field(..., min_length=8)  # Raw password from the client
    email: EmailStr | None = None
    fcm_token: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Updates ---
class UserUpdate(UserBaseSchema):
    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None


# --- Location & FCM ---
class UserLocationUpdate(BaseModel):
    # Geographic bounds enforced at schema level
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class FCMTokenUpdate(BaseModel):
    fcm_token: str | None = Field(None)


# --- Generic responses ---
class MessageResponse(BaseModel):
    message: str
    status: str = "success"
    model_config = ConfigDict(from_attributes=True)


class UserAvatarResponse(BaseModel):
    """Response after avatar upload — returns key or URL as needed."""

    avatar_key: str | None = None
    avatar_url_medium: str | None = None


class AvatarUploadAcceptedResponse(BaseModel):
    """202 response — avatar upload accepted; processing happens in the background."""

    message: str = "Avatar upload accepted"
    status: str = "accepted"


class AvatarUploadUrlRequest(BaseModel):
    """Request a presigned URL for avatar upload."""

    filename: str | None = Field(None, description="Optional filename (for extension hint)")


class AvatarUploadUrlResponse(BaseModel):
    """Response with presigned URL for avatar upload."""

    upload_url: str = Field(..., description="Presigned URL for direct upload to S3")
    staging_key: str = Field(..., description="Staging key for confirm step")
    expires_in: int = Field(300, description="URL TTL in seconds")


class AvatarUploadConfirmRequest(BaseModel):
    """Confirm upload after the client uploaded directly to S3."""

    staging_key: str = Field(..., description="Staging key from upload_url response")
