# תוקף שמירת תצוגת המסלולים (כולל 3 המסלולים) ב-Redis – 24 שעות
RIDE_PREVIEW_TTL = 86400  # 24 שעות (בשניות)

OTP_VERIFICATION_TTL = 600  # 10 דקות


def get_ride_preview_key(session_id: str) -> str:
    return f"ride_preview:{session_id}"


def get_otp_verification_key(user_id: str, event_name: str) -> str:
    """מייצר מפתח אחיד לקוד אימות ב-Redis"""
    return f"otp:{event_name}:{user_id}"


# --- ערוצי Redis — מקור אמת יחיד ---

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
