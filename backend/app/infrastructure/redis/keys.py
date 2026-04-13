from app.core import constants

# Route preview cache TTL (all alternatives) — 24h; see app.core.constants
RIDE_PREVIEW_TTL = constants.RIDE_PREVIEW_TTL

# Legacy key name for verification TTL (same as OTP_TTL)
OTP_VERIFICATION_TTL = constants.OTP_TTL


def get_ride_preview_key(session_id: str) -> str:
    return f"ride_preview:{session_id}"


def get_otp_verification_key(user_id: str, event_name: str) -> str:
    """Build Redis key for OTP / verification codes."""
    return f"otp:{event_name}:{user_id}"


# --- Redis channel naming (single source of truth) ---

RIDES_LIST_CHANNEL = "rides:list"


def get_ride_channel(ride_id) -> str:
    """Pub/sub channel for ride status (driver + passengers)."""
    return f"ride_{ride_id}"


def get_ride_passengers_channel(ride_id) -> str:
    """Channel for passenger live locations toward driver."""
    return f"ride_{ride_id}:passenger_locations"


def get_booking_channel(booking_id) -> str:
    """Channel for driver location updates for a booking."""
    return f"booking_{booking_id}"


def get_user_channel(user_id) -> str:
    """Per-user events fan-out (chat-ws / WebSocket clients)."""
    return f"user:{user_id}:events"
