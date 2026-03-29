import json
import logging
from typing import Dict, Any
from uuid import UUID

from app.infrastructure.redis.broadcast import broadcast
from app.domain.rides.enum import RideStatus, RideBroadcastAction
from app.infrastructure.redis.keys import get_ride_channel

logger = logging.getLogger(__name__)


class RideNotificationFactory:
    _CONFIG = {
        RideBroadcastAction.CREATED.value: {
            "color": "green",
            "message": "נסיעה חדשה זמינה כעת!",
            "event_prefix": "RIDE_CREATED",
        },
        RideBroadcastAction.UPDATED.value: {
            "color": "orange",
            "message": "עדכון בנסיעה (למשל מקום תפוס)",
            "event_prefix": "RIDE_UPDATED",
        },
        RideStatus.CANCELLED.value: {
            "color": "red",
            "message": "הנסיעה בוטלה על ידי הנהג",
            "event_prefix": "RIDE_CANCELLED",
        },
        RideStatus.COMPLETED.value: {
            "color": "green",
            "message": "הנסיעה הסתיימה בהצלחה",
            "event_prefix": "RIDE_COMPLETED",
        },
    }

    @classmethod
    def create_broadcast_payload(cls, ride, action: str) -> Dict[str, Any]:
        config = cls._CONFIG.get(
            action,
            {
                "color": "gray",
                "message": "עדכון בנסיעה",
                "event_prefix": "RIDE_UPDATED",
            },
        )
        return {
            "event": config["event_prefix"],
            "ride_id": str(ride.ride_id),
            "status": ride.status.value
            if hasattr(ride.status, "value")
            else str(ride.status),
            "color": config["color"],
            "message": f"{config['message']} (מ-{ride.origin_name} ל-{ride.destination_name})",
        }


async def publish_ride_event(
    ride_id: UUID,
    event: str,
    extra: dict | None = None,
) -> None:
    """
    נקודת הכניסה היחידה לשידור אירועי סטטוס נסיעה.
    כל שינוי סטטוס עובר דרך כאן בלבד.
    """
    payload = {
        "event": event,
        "ride_id": str(ride_id),
        **(extra or {}),
    }
    try:
        await broadcast.publish(
            get_ride_channel(ride_id),
            json.dumps(payload),
        )
    except Exception as e:
        logger.warning("publish_ride_event failed [%s]: %s", event, e)


async def publish_ride_update(ride_id: UUID, message_data: dict) -> None:
    """Deprecated — השתמש ב-publish_ride_event."""
    event = message_data.get("event", "RIDE_UPDATED")
    extra = {k: v for k, v in message_data.items() if k != "event"}
    await publish_ride_event(ride_id, event, extra)


# TTL ו-key builders (נשארים לתאימות לאחור)
RIDE_PREVIEW_TTL = 86400


def get_ride_preview_key(session_id: str) -> str:
    return f"ride_preview:{session_id}"


OTP_VERIFICATION_TTL = 600


def get_otp_verification_key(user_id: str, event_name: str) -> str:
    return f"otp:{event_name}:{user_id}"
