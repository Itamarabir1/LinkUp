"""
Recipient resolution for notifications — by event_key and source.
Callers must pass source with required relationships loaded (driver, passenger, passenger_request.user).
"""

import logging
from typing import Any

from app.core.exceptions.base import LinkUpError

logger = logging.getLogger(__name__)


class ResolverError(LinkUpError):
    """Failed to resolve notification recipient."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class RecipientResolver:
    """
    Returns the User who should receive the notification (email/push) from:
    - event_key: notification event (NotificationEvent)
    - source: entity from the handler (User / Ride / Booking)

    When passing Ride or Booking, relationships must be loaded:
    - Ride: selectinload(Ride.driver)
    - Booking: selectinload(Booking.ride).selectinload(Ride.driver), selectinload(Booking.passenger_request).selectinload(PassengerRequest.user)
    """

    def resolve(self, event_key: Any, source: Any) -> Any | None:
        """
        Returns recipient User or None.
        strategy["role"]: self → source is User; driver → driver from Ride/Booking; passenger → passenger from Booking.
        """
        from app.domain.notifications.config.mappings import NOTIFICATION_STRATEGY

        strategy = NOTIFICATION_STRATEGY.get(event_key)
        if not strategy:
            logger.warning("No strategy for event_key=%s", event_key)
            return None
        role = strategy.get("role")
        if not role:
            logger.warning("Strategy has no role for event_key=%s", event_key)
            return None
        if role == "self":
            return self._for_self(source)
        if role == "driver":
            return self._get_driver(source)
        if role == "passenger":
            return self._get_passenger(source)
        if role == "both":
            return self._get_both(source)
        raise ResolverError(f"Role {role!r} not supported")

    def _for_self(self, source: Any) -> Any:
        """role=self: source is User — return it."""
        return source

    def _get_driver(self, source: Any) -> Any | None:
        """
        role=driver: source is Ride or Booking.
        Ride: requires source.driver (or returns None).
        Booking: requires source.ride and source.ride.driver.
        """
        if source is None:
            return None
        if hasattr(source, "ride") and source.ride is not None:
            return getattr(source.ride, "driver", None)
        if hasattr(source, "driver"):
            return source.driver
        return None

    def _get_passenger(self, source: Any) -> Any | None:
        """
        role=passenger: source is Booking (or an entity with passenger/passenger_request).
        Requires source.passenger or source.passenger_request.user.
        """
        if source is None:
            return None
        if hasattr(source, "passenger") and source.passenger is not None:
            return source.passenger
        if hasattr(source, "passenger_request") and source.passenger_request is not None:
            return getattr(source.passenger_request, "user", None)
        return None

    def _get_both(self, source: Any) -> Any | None:
        """
        role=both: source is a payload dict with user_id_1 and user_id_2.
        Returns that dict (or None if not applicable); the handler sends to both users.
        """
        if source is None:
            return None
        # If source is a dict with user_id_1 and user_id_2, return the dict as-is
        # The handler will send to both users
        if isinstance(source, dict) and "user_id_1" in source and "user_id_2" in source:
            return source
        return None


recipient_resolver = RecipientResolver()
