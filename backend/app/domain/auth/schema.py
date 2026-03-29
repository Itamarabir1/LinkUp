from typing import Optional
from uuid import UUID
from pydantic import (
    BaseModel,
    EmailStr,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)
from app.core.config import settings

from app.core.utils.validators import (
    normalize_email_for_auth,
    validate_password_strength,
    validate_phone_number,
)

# --- Request Schemas (DTOs) ---


class UserRegister(BaseModel):
    """
    סכמת רישום – מה שהלקוח (פרונט) שולח.
    fcm_token אופציונלי – האפליקציה שולחת מהקוד (הרשאות פוש), לא משדה שהמשתמש ממלא.
    """

    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    fcm_token: Optional[str] = Field(
        None,
        description="לשימוש האפליקציה בלבד (הרשאות פוש). לא להציג למשתמש בטופס רישום.",
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
        """מוודא ששני שדות הסיסמה זהים"""
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
    email: Optional[EmailStr] = None  # אופציונלי - יכול לבוא מ-cookie
    code: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_email_for_auth(v)


class PasswordResetRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
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
        """מוודא ששני שדות הסיסמה החדשים זהים"""
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class ChangePasswordRequest(BaseModel):
    """
    שינוי סיסמה (משתמש מחובר): סיסמה ישנה + סיסמה חדשה פעמיים.
    ולידציה כמו ברישום: חוזק סיסמה + התאמה בין שני שדות הסיסמה החדשה.
    """

    old_password: str = Field(..., min_length=1, description="הסיסמה הנוכחית")
    new_password: str = Field(..., min_length=8, description="סיסמה חדשה")
    confirm_password: str = Field(..., min_length=8, description="אישור הסיסמה החדשה")

    @field_validator("new_password")
    @classmethod
    def check_new_password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def verify_passwords_match_and_different(self) -> "ChangePasswordRequest":
        """מוודא ששתי הסיסמאות החדשות זהות (כמו ברישום) והסיסמה החדשה שונה מהישנה."""
        from app.core.exceptions.auth import (
            PasswordsDoNotMatchError,
            NewPasswordSameAsOldError,
        )

        if self.new_password != self.confirm_password:
            raise PasswordsDoNotMatchError()
        if self.new_password == self.old_password:
            raise NewPasswordSameAsOldError()
        return self


# --- Response Schemas ---


def _avatar_url_medium_from_key(avatar_key: Optional[str]) -> Optional[str]:
    if not avatar_key or not settings.S3_BUCKET_NAME:
        return None
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{avatar_key}400x400.webp"


class UserOut(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    phone_number: str
    is_verified: bool
    avatar_key: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def avatar_url(self) -> Optional[str]:
        """תאימות לאחור — מחזיר URL ל-400x400."""
        return _avatar_url_medium_from_key(self.avatar_key)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginUserInfo(BaseModel):
    """פרטי משתמש בתשובות login / google-signin / refresh (כולל הרשאת אדמין לפרונט)."""

    user_id: UUID
    full_name: str
    email: EmailStr
    is_admin: bool = False


class LoginResponse(BaseModel):
    """תשובת לוגין: Access Token (קצר) + Refresh Token (ארוך) + פרטי משתמש."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: LoginUserInfo


class RefreshRequest(BaseModel):
    """בקשת Access Token חדש באמצעות Refresh Token."""

    refresh_token: str = Field(..., description="ה-Refresh Token שהתקבל ב-login")


class RefreshResponse(BaseModel):
    """תשובה מ-POST /auth/refresh – Access Token חדש (+ אופציונלי Refresh Token חדש) ופרטי משתמש."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: LoginUserInfo


class AuthMessageResponse(BaseModel):
    message: str
    status: str = "success"


class PasswordResetConfirmResponse(BaseModel):
    """תשובה אחרי אישור שחזור סיסמה – מוצגת בפרונט/Swagger כאובייקט מובנה."""

    message: str = Field(..., description="הודעת הצלחה")
    status: str = Field(default="success", description="סטטוס התגובה")
    detail: Optional[str] = Field(
        default=None, description="פירוט אופציונלי (למשל להצגה בפרונט)"
    )


class EmailOnlyRequest(BaseModel):
    """
    סכמה המשמשת לבקשות הדורשות רק כתובת אימייל,
    כמו שליחה חוזרת של קוד אימות או בקשת שחזור סיסמה.
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
    """בקשת התחברות דרך Google OAuth - מקבל ID token מ-Google Sign-In."""

    id_token: str = Field(
        ..., min_length=100, description="Google ID token (JWT) מ-Google Sign-In"
    )
