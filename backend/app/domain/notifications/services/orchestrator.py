# app/domain/notifications/services/orchestrator.py
import logging

from app.core.exceptions import NotificationError
from app.domain.rides.model import Ride
from app.infrastructure.events.dispatcher.base import dispatch

logger = logging.getLogger(__name__)


class NotificationOrchestrator:
    async def notify_ride_cancelled(self, ride: Ride):
        # Business filter: who should actually be notified
        active_bookings = [b for b in ride.bookings if b.status != "cancelled"]

        if not active_bookings:
            logger.info(f"No active passengers for ride {ride.id}, skipping notification.")
            return

        try:
            # Event name must match handler registry strings
            await dispatch(
                event_name="ride.cancelled",  # תואם ל-NotificationEvent.RIDE_CANCELLED
                payload={
                    "ride_id": ride.id,
                    # Handler hydrates from ride_id; resolver loads passengers
                },
            )
        except Exception as e:
            logger.exception("Failed to dispatch ride.cancelled notification: %s", e)
            raise NotificationError(f"Failed to dispatch cancellation: {e!s}") from e
