import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from uuid import UUID

from app.infrastructure.redis.broadcast import broadcast
from app.domain.geo.schema import LocationUpdate

logger = logging.getLogger(__name__)

PASSENGER_LOCATIONS_CHANNEL_SUFFIX = ":passenger_locations"


async def broadcast_location_to_participants(
    location_in: LocationUpdate, ride_id: UUID, involved_bookings: List[UUID]
) -> Dict[str, Any]:
    """
    מפיץ את המיקום בזמן אמת לכל הנוסעים הרשומים לנסיעה דרך ה-WebSockets.

    אחריות:
    1. יצירת הודעת JSON סטנדרטית.
    2. שימוש ב-Timestamp מבוסס UTC (Timezone-aware).
    3. הפצה לכל ערוצי הבוקינג הרלוונטיים ב-Redis.
    """

    # הכנת גוף ההודעה - שימוש ב-datetime.now(timezone.utc) במקום utcnow() המיושן
    payload = {
        "type": "location_update",
        "ride_id": str(ride_id),
        "lat": location_in.latitude,
        "lng": location_in.longitude,
        "heading": location_in.heading or 0.0,
        "speed": location_in.speed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    message_json = json.dumps(payload)

    try:
        # לולאה על כל הבוקינגים הפעילים בנסיעה הזו
        for booking_id in involved_bookings:
            channel_name = f"booking_{str(booking_id)}"

            # פרסום ל-Redis Pub/Sub דרך ה-Broadcast manager
            await broadcast.publish(channel=channel_name, message=message_json)

        return payload

    except Exception as e:
        logger.error(f"❌ Failed to broadcast location for ride {ride_id}: {e}")
        # ב-Real-time עדיף להיכשל שקט ולא להפיל את כל ה-Request
        return payload


async def broadcast_passenger_location_to_driver(
    ride_id: UUID,
    booking_id: UUID,
    passenger_id: UUID,
    lat: float,
    lng: float,
    heading: float = 0.0,
    speed: float = 0.0,
) -> Dict[str, Any]:
    """
    מפיץ מיקום נוסע לנהג – פרסום לערוץ ride_{ride_id}:passenger_locations.
    הנהג מאזין ב-WebSocket /ws/ride/{ride_id}/passengers.
    """
    payload = {
        "type": "passenger_location",
        "ride_id": str(ride_id),
        "booking_id": str(booking_id),
        "passenger_id": str(passenger_id),
        "lat": lat,
        "lng": lng,
        "heading": heading,
        "speed": speed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    message_json = json.dumps(payload)
    channel_name = f"ride_{ride_id}{PASSENGER_LOCATIONS_CHANNEL_SUFFIX}"
    try:
        await broadcast.publish(channel=channel_name, message=message_json)
    except Exception as e:
        logger.error(
            "❌ Failed to broadcast passenger location for ride %s: %s",
            ride_id,
            e,
        )
    return payload
