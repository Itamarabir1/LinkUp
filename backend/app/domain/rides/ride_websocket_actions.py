import logging

from app.domain.notifications.core.builders.ride_builder import RideBuilder
from app.domain.rides.model import Ride
from app.infrastructure.redis.publisher import publish_ride_event

logger = logging.getLogger(__name__)


class RideActions:
    """
    Ride-side actions (WebSocket, etc.).
    Email/push events are emitted via Outbox from the service layer.
    """

    @staticmethod
    def _get_ride_id(ride: Ride) -> str:
        return str(getattr(ride, "ride_id", ride))

    @staticmethod
    async def handle_cancellation(ride: Ride) -> None:
        """WebSocket publish only. Outbox events are handled in the cancellation service."""
        try:
            context = RideBuilder().build(ride, event_key="ride_cancelled")
            await publish_ride_event(
                ride.ride_id,
                "RIDE_CANCELLED",
                {"data": context},
            )
        except Exception as e:
            logger.warning("handle_cancellation WS failed: %s", e)
