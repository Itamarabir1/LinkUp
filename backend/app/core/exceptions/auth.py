from fastapi import status

from .base import LinkupError


class SessionExpiredError(LinkupError):
    status_code = 401
    error_code = "AUTH_SESSION_EXPIRED"
    message = "הסשן פג תוקף, אנא התחבר שוב"


class InvalidAccessTokenError(LinkupError):
    """JWT invalid, expired, or missing `sub` — mirrors checks in `get_current_user`."""

    status_code = 401
    error_code = "INVALID_TOKEN"
    message = "אסימון לא תקף או פג תוקף"


class UserInactiveOrMissingError(LinkupError):
    status_code = 401
    error_code = "AUTH_USER_INACTIVE_OR_MISSING"
    message = "המשתמש לא נמצא או אינו פעיל"


class PermissionDeniedError(LinkupError):
    status_code = 403
    error_code = "AUTH_PERMISSION_DENIED"
    message = "אין הרשאה לביצוע הפעולה"


class InvalidVerificationCodeError(LinkupError):
    status_code = 400
    error_code = "AUTH_INVALID_CODE"
    message = "קוד האימות שגוי או פג תוקף"


class InvalidCredentialsError(LinkupError):
    status_code = 401
    error_code = "AUTH_INVALID_CREDENTIALS"
    message = "אימייל או סיסמה שגויים"

    def __init__(self):
        # No payload — avoid leaking info to attackers
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )


class UserNotVerifiedError(LinkupError):
    status_code = 403
    error_code = "AUTH_USER_NOT_VERIFIED"
    message = "החשבון עדיין לא עבר אימות"

    def __init__(self, email: str):
        # Include email so the user knows which address the code was sent to
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
            payload={"email": email},
        )


class InvalidResetCodeError(LinkupError):
    status_code = 400
    error_code = "AUTH_INVALID_RESET_CODE"
    message = "קוד שחזור הסיסמה שגוי או פג תוקף"

    def __init__(self, email: str | None = None):
        super().__init__(message=self.message, payload={"email": email} if email else None)


class InvalidRefreshTokenError(LinkupError):
    status_code = 401
    error_code = "AUTH_INVALID_REFRESH_TOKEN"
    message = "Refresh Token שגוי או פג תוקף – יש להתחבר מחדש"

    def __init__(self):
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )


class InvalidPasswordError(LinkupError):
    status_code = 401
    error_code = "INVALID_PASSWORD"
    message = "הסיסמה הישנה שהוזנה אינה נכונה"

    def __init__(self):
        super().__init__(message=self.message, status_code=self.status_code)


class PasswordTooWeakError(LinkupError):
    def __init__(self, details: str = None):
        description = details or "על הסיסמה להכיל לפחות 8 תווים, אות גדולה, קטנה, מספר ותו מיוחד"
        super().__init__(
            message=f"הסיסמה חלשה מדי: {description}",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="AUTH_PASSWORD_TOO_WEAK",
        )


class PasswordsDoNotMatchError(LinkupError):
    def __init__(self):
        super().__init__(
            message="הסיסמה החדשה והאישור אינם זהים",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="AUTH_PASSWORDS_MISMATCH",
        )


class NewPasswordSameAsOldError(LinkupError):
    def __init__(self):
        super().__init__(
            message="הסיסמה החדשה חייבת להיות שונה מהישנה",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="AUTH_SAME_PASSWORD",
        )


class VerificationCodeExpiredError(LinkupError):
    status_code = 400
    error_code = "AUTH_OTP_EXPIRED"
    message = "פג תוקף קוד האימות, אנא בקש קוד חדש"

    def __init__(self):
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
        )


class GoogleAuthFailed(LinkupError):
    """Failure authenticating with Google — external service, not the user's fault."""

    status_code = 502
    error_code = "AUTH_GOOGLE_FAILED"
    message = "אימות Google נכשל, נסה שוב מאוחר יותר"
