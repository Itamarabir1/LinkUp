import logging

from app.domain.notifications.core.builders.ride_builder import RideBuilder
from app.domain.rides.broadcast import publish_ride_event
from app.domain.rides.model import Ride

logger = logging.getLogger(__name__)


class RideActions:
    """
    פעולות על נסיעות (WebSocket, וכו').
    אירועים למיילים/פוש נשלחים דרך Outbox מהשירות.
    """

    @staticmethod
    def _get_ride_id(ride: Ride) -> str:
        return str(getattr(ride, "ride_id", ride))

    @staticmethod
    async def handle_cancellation(ride: Ride) -> None:
        """שליחה ל-WebSocket בלבד. אירועי Outbox מטופלים בשירות הביטול."""
        try:
            context = RideBuilder().build(ride, event_key="ride_cancelled")
            await publish_ride_event(
                ride.ride_id,
                "RIDE_CANCELLED",
                {"data": context},
            )
        except Exception as e:
            logger.warning("handle_cancellation WS failed: %s", e)
