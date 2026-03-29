import logging
from typing import Any, Dict, Optional
from datetime import datetime
from .base import BaseContextBuilder

logger = logging.getLogger(__name__)


def _format_datetime(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M")
    return str(dt) if dt else "—"


def _get_attr_path(obj: Any, path: str, default: Any = "") -> Any:
    """Safe path resolution (e.g. 'passenger_request.user.full_name') without relying on base class method."""
    if obj is None:
        return default
    current = obj
    for attr in path.split("."):
        current = getattr(current, attr, None)
        if current is None:
            return default
    return current


class BookingBuilder(BaseContextBuilder):
    """
    Booking Context Transformer.
    אחראי על המרת אובייקט Booking למילון נתונים עבור התראות.
    בונה קונטקסט הנסיעה (origin, destination, ride_date, driver_name) ישירות מ־ride.
    """

    @classmethod
    def build(cls, booking: Any, event_key: Optional[str] = None) -> Dict[str, Any]:
        """
        בונה קונטקסט מלא מהזמנה.
        """
        if not booking:
            logger.error("BookingContextBuilder: Received None as booking object")
            return {}

        inst = cls()
        ride = getattr(booking, "ride", None)
        event_key_str = event_key if isinstance(event_key, str) else (event_key or "")
        context = {}
        if ride:
            ride_id_val = getattr(ride, "ride_id", None) or getattr(ride, "id", "")
            context = {
                "ride_id": ride_id_val,
                "origin": getattr(ride, "origin_name", "N/A"),
                "destination": getattr(ride, "destination_name", "N/A"),
                "ride_date": inst._format_date(getattr(ride, "departure_time", None)),
                "driver_name": _get_attr_path(ride, "driver.first_name", "נהג"),
                "ride_url": inst._get_cta_url(f"rides/{ride_id_val}"),
                "color": inst._determine_color(event_key_str),
            }

        booking_id = getattr(booking, "booking_id", None) or getattr(booking, "id", "")
        ride_id = getattr(ride, "ride_id", None) or context.get("ride_id", "")

        pickup_time = getattr(booking, "pickup_time", None)
        if not pickup_time and ride:
            pickup_time = getattr(ride, "departure_time", None)

        passenger_name = (
            _get_attr_path(booking, "passenger_request.user.full_name", None)
            or _get_attr_path(booking, "passenger_request.user.first_name", None)
            or _get_attr_path(booking, "passenger.full_name", None)
            or _get_attr_path(booking, "passenger.first_name", None)
        )
        if not passenger_name or (isinstance(passenger_name, str) and not passenger_name.strip()):
            passenger_name = "נוסע"
        context.update(
            {
                "booking_id": booking_id,
                "ride_id": ride_id,
                "num_seats": getattr(booking, "num_seats", 1),
                "passenger_name": passenger_name.strip() if isinstance(passenger_name, str) else str(passenger_name),
                "pickup_name": getattr(booking, "pickup_name", None) or _get_attr_path(booking, "passenger_request.pickup_name", "—"),
                "pickup_time": _format_datetime(pickup_time),
                "ride_date": context.get("ride_date") or _format_datetime(getattr(ride, "departure_time", None)),
                "passenger_destination": _get_attr_path(
                    booking,
                    "passenger_request.destination_name",
                    context.get("destination", "—"),
                ),
                "action_url": inst._get_cta_url("my-bookings?tab=driver"),
                "is_urgent": "urgent" in (event_key or "").lower(),
            }
        )

        return context
