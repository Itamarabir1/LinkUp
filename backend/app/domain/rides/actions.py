from app.infrastructure.websocket_bus import ws_infra
from app.domain.notifications.core.builders.facade import NotificationContext
from app.domain.rides.model import Ride


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
        context = NotificationContext.ride(ride, event_key="RIDE_CANCELLED")
        await ws_infra.publish(
            f"ride_{ride.ride_id}",
            {"type": "RIDE_CANCELLED", "data": context},
        )
