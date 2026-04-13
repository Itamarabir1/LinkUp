"""
Shared validation helpers (email, password, phone, uploads) for auth schemas and API deps.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import UploadFile

try:
    import phonenumbers
except ImportError:
    phonenumbers = None  # type: ignore

# --- Email ---

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def validate_email_format(email: str) -> str:
    """Validate ASCII-style email format."""
    if not email:
        raise ValueError("אימייל לא יכול להיות ריק")
    email = email.strip().lower()
    if not EMAIL_REGEX.match(email):
        raise ValueError("פורמט אימייל לא תקין")
    return email


def normalize_email_for_auth(value: str) -> str:
    """Strip, lower, and validate email for auth flows."""
    v = (value or "").strip().lower()
    return validate_email_format(v)


# --- Password ---

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")
PASSWORD_ERROR = (
    "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character (@$!%*?&)."
)


def validate_password_strength(password: str) -> str:
    """Checks password strength: 8+ characters, upper/lowercase, digit, special character."""
    if not password:
        raise ValueError("סיסמה לא יכולה להיות ריקה")
    if not PASSWORD_REGEX.match(password):
        raise ValueError(PASSWORD_ERROR)
    return password


# --- Phone (E.164) ---


def validate_phone_number(value: str) -> str:
    """Parse international phone numbers to E.164 (default region IL)."""
    if not value or not value.strip():
        raise ValueError("מספר טלפון הוא שדה חובה")
    if phonenumbers is None:
        raise ValueError("phonenumbers לא מותקן – התקן phonenumbers")
    try:
        parsed = phonenumbers.parse(value.strip(), "IL")
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("פורמט טלפון לא תקין")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        raise ValueError("מספר טלפון חייב להיות בינלאומי תקין (למשל +972...)")


def validate_israeli_phone_number(phone: str) -> str:
    """Normalize Israeli mobile numbers to 05XXXXXXXX."""
    if not phone:
        raise ValueError("מספר טלפון הוא שדה חובה")

    clean_val = re.sub(r"[\s\-]", "", phone)
    pattern = r"^(?:05\d{8}|(?:\+?972)5\d{8})$"

    if not re.match(pattern, clean_val):
        raise ValueError("מספר טלפון ישראלי לא תקין")

    if clean_val.startswith("+972"):
        clean_val = "0" + clean_val[4:]
    elif clean_val.startswith("972"):
        clean_val = "0" + clean_val[3:]

    return clean_val


def validate_future_datetime(dt: datetime) -> datetime:
    """Ensure datetime is in the future (UTC-aware)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    now_utc = datetime.now(UTC)
    if dt < now_utc + timedelta(seconds=10):
        raise ValueError("עליך לבחור זמן עתידי")

    return dt


def validate_israeli_license_plate(plate: str) -> str:
    """Validate Israeli license plate as 7–8 digits."""
    clean_plate = re.sub(r"[\s\-]", "", plate)
    if not re.match(r"^\d{7,8}$", clean_plate):
        raise ValueError("מספר רכב לא תקין - יש להזין 7 או 8 ספרות")
    return clean_plate


# --- Avatar / Upload file ---

MAX_AVATAR_SIZE_MB: int = 5
ALLOWED_AVATAR_CONTENT_TYPES: tuple[str, ...] = (
    "image/jpeg",
    "image/png",
    "image/webp",
)


def validate_avatar_file(file: "UploadFile") -> None:
    """
    Validates avatar file type and maximum size.
    Raises InvalidFileTypeError / FileTooLargeError.
    Used as a Dependency (api/dependencies/file) or called directly.
    """
    from app.core.exceptions.validation import FileTooLargeError, InvalidFileTypeError

    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise InvalidFileTypeError(content_type=file.content_type or "")

    max_bytes = MAX_AVATAR_SIZE_MB * 1024 * 1024
    actual_size = getattr(file, "size", 0) or 0
    if actual_size > max_bytes:
        current_mb = round(actual_size / (1024 * 1024), 2)
        raise FileTooLargeError(max_size_mb=MAX_AVATAR_SIZE_MB, current_size_mb=current_mb)


def slugify_for_avatar(name: str | None) -> str:
    """
    Returns a safe filename slug for avatar names: lowercase, hyphens, Hebrew characters allowed.
    If empty — returns an empty string (caller should fall back to user_id).
    """
    if not name or not (s := name.strip()):
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\-_\u0590-\u05ff]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s if s else ""
