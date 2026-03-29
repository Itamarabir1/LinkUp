"""
מקור אמת יחיד לולידציות: אימות (מייל, סיסמה, טלפון), קבצים (אווטאר), ועוד.
משמש את domain/auth/schema, api/dependencies/file וכל מקום שדורש ולידציה אחידה בלי כפילות.
"""

import re
from datetime import datetime, timezone, timedelta
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
    """מאמת פורמט אימייל (אנגלית/מספרים/תווים סטנדרטיים, ללא עברית)."""
    if not email:
        raise ValueError("אימייל לא יכול להיות ריק")
    email = email.strip().lower()
    if not EMAIL_REGEX.match(email):
        raise ValueError("פורמט אימייל לא תקין")
    return email


def normalize_email_for_auth(value: str) -> str:
    """נורמליזציה + ולידציה למייל ברישום/התחברות/אימות – strip, lower, validate."""
    v = (value or "").strip().lower()
    return validate_email_format(v)


# --- Password ---

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")
PASSWORD_ERROR = (
    "Password must be at least 8 characters long, include an uppercase letter, a lowercase letter, a number, and a special character (@$!%*?&)."
)


def validate_password_strength(password: str) -> str:
    """בודק חוזק סיסמה: 8+ תווים, אות גדולה/קטנה, מספר, תו מיוחד."""
    if not password:
        raise ValueError("סיסמה לא יכולה להיות ריקה")
    if not PASSWORD_REGEX.match(password):
        raise ValueError(PASSWORD_ERROR)
    return password


# --- Phone (E.164) ---


def validate_phone_number(value: str) -> str:
    """מאמת טלפון בינלאומי ומנרמל לפורמט E.164 (למשל +972...)."""
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
    """מנקה ומאמת טלפון ישראלי לפורמט 05XXXXXXXX."""
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
    """בודק שהזמן שנבחר הוא עתידי (UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now_utc = datetime.now(timezone.utc)
    if dt < now_utc + timedelta(seconds=10):
        raise ValueError("עליך לבחור זמן עתידי")

    return dt


def validate_israeli_license_plate(plate: str) -> str:
    """מאמת לוחית רישוי (7 או 8 ספרות)."""
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
    בודק סוג קובץ וגודל מקסימלי לאווטאר.
    משליך InvalidFileTypeError / FileTooLargeError.
    משמש כ-Dependency (api/dependencies/file) או קריאה ישירה.
    """
    from app.core.exceptions.validation import InvalidFileTypeError, FileTooLargeError

    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise InvalidFileTypeError(content_type=file.content_type or "")

    max_bytes = MAX_AVATAR_SIZE_MB * 1024 * 1024
    actual_size = getattr(file, "size", 0) or 0
    if actual_size > max_bytes:
        current_mb = round(actual_size / (1024 * 1024), 2)
        raise FileTooLargeError(max_size_mb=MAX_AVATAR_SIZE_MB, current_size_mb=current_mb)


def slugify_for_avatar(name: str | None) -> str:
    """
    מחזיר slug בטוח לשם קובץ אווטאר: אותיות קטנות, מקפים, תומך בעברית.
    אם ריק – מחזיר מחרוזת ריקה (הקריאה תשתמש ב-user_id כ-fallback).
    """
    if not name or not (s := name.strip()):
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\-_\u0590-\u05ff]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s if s else ""
