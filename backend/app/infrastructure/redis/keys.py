from app.core import constants

# Route preview cache TTL (all alternatives) — 24h; see app.core.constants
RIDE_PREVIEW_TTL = constants.RIDE_PREVIEW_TTL

# Legacy key name for verification TTL (same as OTP_TTL)
OTP_VERIFICATION_TTL = constants.OTP_TTL


def get_ride_preview_key(session_id: str) -> str:
    return f"ride_preview:{session_id}"


def get_otp_verification_key(user_id: str, event_name: str) -> str:
    """מייצר מפתח אחיד לקוד אימות ב-Redis"""
    return f"otp:{event_name}:{user_id}"


# --- Redis channel naming (single source of truth) ---

RIDES_LIST_CHANNEL = "rides:list"


def get_ride_channel(ride_id) -> str:
    """אירועי סטטוס נסיעה → נוסעים ונהג."""
    return f"ride_{ride_id}"


def get_ride_passengers_channel(ride_id) -> str:
    """מיקומי נוסעים → נהג."""
    return f"ride_{ride_id}:passenger_locations"


def get_booking_channel(booking_id) -> str:
    """מיקום נהג → נוסע ספציפי."""
    return f"booking_{booking_id}"


def get_user_channel(user_id) -> str:
    """אירועי משתמש אישיים → chat-ws → WS client."""
    return f"user:{user_id}:events"
