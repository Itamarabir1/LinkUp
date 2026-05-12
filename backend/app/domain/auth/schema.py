from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.utils.validators import (
    normalize_email_for_auth,
    validate_password_strength,
    validate_phone_number,
)
from app.infrastructure.s3.service import storage_service

# --- Request Schemas (DTOs) ---


class UserRegister(BaseModel):
    """
    Registration payload from the client.
    Optional fcm_token is supplied by the app (push permission), not a user-typed field.
    """

    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    fcm_token: str | None = Field(
        None,
        description="App-only (push registration); not shown on signup form.",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return normalize_email_for_auth(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("phone_number")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return validate_phone_number(v)

    @model_validator(mode="after")
    def verify_passwords_match(self) -> "UserRegister":
        """Ensure password and confirmation match."""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return normalize_email_for_auth(v)


class VerifyEmailRequest(BaseModel):
    email: EmailStr | None = None  # Optional; may come from cookie after register
    code: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_email_for_auth(v)


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return normalize_email_for_auth(v)

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def verify_reset_passwords_match(self) -> "PasswordResetConfirm":
        """Ensure new password fields match."""
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordRequest(BaseModel):
    """
    Authenticated password change: current password + new password twice.
    Same strength rules as registration; new fields must match.
    """

    old_password: str = Field(..., min_length=1, description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")
    confirm_password: str = Field(..., min_length=8, description="Confirm new password")

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def verify_passwords_match_and_different(self) -> "ChangePasswordRequest":
        """New passwords must match and differ from the old password."""
        from app.core.exceptions.auth import (
            NewPasswordSameAsOldError,
            PasswordsDoNotMatchError,
        )

        if self.new_password != self.confirm_password:
            raise PasswordsDoNotMatchError()
        if self.new_password == self.old_password:
            raise NewPasswordSameAsOldError()
        return self


# --- Response Schemas ---


def _avatar_url_medium_from_key(avatar_key: str | None) -> str | None:
    return storage_service.build_avatar_url(avatar_key, "400x400.webp")


class UserOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    is_verified: bool
    avatar_key: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url(self) -> str | None:
        """Backward-compatible medium avatar URL (400x400)."""
        return _avatar_url_medium_from_key(self.avatar_key)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginUserInfo(BaseModel):
    """User summary returned on login, Google sign-in, and refresh (includes is_admin)."""

    user_id: UUID
    full_name: str
    email: EmailStr
    is_admin: bool = False


class LoginResponse(BaseModel):
    """Login response: short-lived access token and user info."""

    access_token: str
    token_type: str = "bearer"
    user: LoginUserInfo


class RefreshRequest(BaseModel):
    """Exchange a refresh token for a new access token (sent via HttpOnly cookie)."""


class RefreshResponse(BaseModel):
    """POST /auth/refresh response: new access token and user info."""

    access_token: str
    token_type: str = "bearer"
    user: LoginUserInfo


class AuthMessageResponse(BaseModel):
    message: str
    status: str = "success"


class PasswordResetConfirmResponse(BaseModel):
    """Structured success payload after password reset confirmation."""

    message: str = Field(..., description="Success message")
    status: str = Field(default="success", description="Response status flag")
    detail: str | None = Field(default=None, description="Optional extra detail for clients")


class EmailOnlyRequest(BaseModel):
    """
    Body for flows that only need an email (resend verification, password reset request).
    """

    email: EmailStr = Field(
        ...,
        json_schema_extra={"example": "user@example.com"},
        description="The user's email address",
    )

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return normalize_email_for_auth(v)


class GoogleSignInRequest(BaseModel):
    """Google Sign-In: verify using Google's ID token (JWT)."""

    id_token: str = Field(..., min_length=100, description="Google ID token (JWT) from Sign-In")
