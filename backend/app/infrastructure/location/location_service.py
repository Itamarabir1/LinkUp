import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.domain.geo.schema import LocationUpdate
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.keys import get_booking_channel, get_ride_passengers_channel

logger = logging.getLogger(__name__)


async def broadcast_location_to_participants(location_in: LocationUpdate, ride_id: UUID, involved_bookings: list[UUID]) -> dict[str, Any]:
    payload = {
        "type": "location_update",
        "ride_id": str(ride_id),
        "lat": location_in.latitude,
        "lng": location_in.longitude,
        "heading": location_in.heading or 0.0,
        "speed": location_in.speed,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    message_json = json.dumps(payload)
    try:
        for booking_id in involved_bookings:
            await broadcast.publish(
                channel=get_booking_channel(booking_id),
                message=message_json,
            )
    except Exception as e:
        logger.error("Failed to broadcast location for ride %s: %s", ride_id, e)
    return payload


async def broadcast_passenger_location_to_driver(
    ride_id: UUID,
    booking_id: UUID,
    passenger_id: UUID,
    lat: float,
    lng: float,
    heading: float = 0.0,
    speed: float = 0.0,
) -> dict[str, Any]:
    payload = {
        "type": "passenger_location",
        "ride_id": str(ride_id),
        "booking_id": str(booking_id),
        "passenger_id": str(passenger_id),
        "lat": lat,
        "lng": lng,
        "heading": heading,
        "speed": speed,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    try:
        await broadcast.publish(
            channel=get_ride_passengers_channel(ride_id),
            message=json.dumps(payload),
        )
    except Exception as e:
        logger.error("Failed to broadcast passenger location for ride %s: %s", ride_id, e)
    return payload
