from uuid import UUID

from .base import LinkUpError


class UserNotFoundError(LinkUpError):
    status_code = 404
    error_code = "USER_NOT_FOUND"
    message = "המשתמש המבוקש לא נמצא במערכת"

    def __init__(self, user_id: UUID | str | None = None, identifier: str | None = None):
        msg = self.message
        payload = {}
        if user_id is not None:
            msg = f"{self.message} (ID: {user_id})"
            payload["user_id"] = user_id
        if identifier is not None:
            msg = f"{self.message} (מזהה: {identifier})"
            payload["identifier"] = identifier
        super().__init__(message=msg, payload=payload or None)


class PhoneAlreadyRegisteredError(LinkUpError):
    status_code = 400
    error_code = "USER_PHONE_TAKEN"
    message = "מספר הטלפון כבר רשום במערכת"

    def __init__(self, phone: str):
        super().__init__(message=f"{self.message}: {phone}", payload={"phone": phone})


class EmailAlreadyRegisteredError(LinkUpError):
    status_code = 400
    error_code = "USER_EMAIL_TAKEN"
    message = "כתובת האימייל כבר רשומה במערכת"

    def __init__(self, email: str):
        super().__init__(message=f"{self.message}: {email}", payload={"email": email})


class PasswordsDoNotMatchError(LinkUpError):
    status_code = 400
    error_code = "USER_PASSWORDS_MISMATCH"
    message = "הסיסמה החדשה ואישור הסיסמה אינם זהים"


class PasswordSameAsOldError(LinkUpError):
    status_code = 400
    error_code = "USER_PASSWORD_SAME_AS_OLD"
    message = "הסיסמה החדשה חייבת להיות שונה מהסיסמה הנוכחית"
