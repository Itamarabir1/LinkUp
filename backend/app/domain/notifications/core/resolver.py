"""
זיהוי נמען להודעות – לפי event_key ו־source.
הקריאה חייבת להעביר source עם relationships טעונים (driver, passenger, passenger_request.user).
"""

import logging
from typing import Any, Optional
from app.core.exceptions.base import LinkupError

logger = logging.getLogger(__name__)


class ResolverError(LinkupError):
    """שגיאה בזיהוי נמען."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class RecipientResolver:
    """
    מחזיר את ה־User שצריך לקבל את ההודעה (מייל/פוש) לפי:
    - event_key: מפתח האירוע (NotificationEvent)
    - source: הישות שה־Handler הביא (User / Ride / Booking)

    דרישה: כשמועבר Ride או Booking, יש לטעון relationships:
    - Ride: selectinload(Ride.driver)
    - Booking: selectinload(Booking.ride).selectinload(Ride.driver), selectinload(Booking.passenger_request).selectinload(PassengerRequest.user)
    """

    def resolve(self, event_key: Any, source: Any) -> Optional[Any]:
        """
        מחזיר User (נמען) או None.
        strategy["role"] קובע: self → source הוא User; driver → נהג מה־Ride/Booking; passenger → נוסע מה־Booking.
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
        """role=self: source הוא User – מחזירים אותו."""
        return source

    def _get_driver(self, source: Any) -> Optional[Any]:
        """
        role=driver: source הוא Ride או Booking.
        Ride: נדרש source.driver (או נחזיר None).
        Booking: נדרש source.ride ו־source.ride.driver.
        """
        if source is None:
            return None
        if hasattr(source, "ride") and source.ride is not None:
            return getattr(source.ride, "driver", None)
        if hasattr(source, "driver"):
            return source.driver
        return None

    def _get_passenger(self, source: Any) -> Optional[Any]:
        """
        role=passenger: source הוא Booking (או ישות עם passenger/passenger_request).
        נדרש source.passenger או source.passenger_request.user.
        """
        if source is None:
            return None
        if hasattr(source, "passenger") and source.passenger is not None:
            return source.passenger
        if hasattr(source, "passenger_request") and source.passenger_request is not None:
            return getattr(source.passenger_request, "user", None)
        return None

    def _get_both(self, source: Any) -> Optional[Any]:
        """
        role=both: source הוא payload dict עם user_id_1 ו-user_id_2.
        מחזיר list של שני משתמשים (או None אם לא ניתן לזהות).
        """
        if source is None:
            return None
        # אם source הוא dict עם user_id_1 ו-user_id_2, נחזיר את ה-dict עצמו
        # ה-handler יטפל בשליחה לשני המשתמשים
        if isinstance(source, dict) and "user_id_1" in source and "user_id_2" in source:
            return source
        return None


recipient_resolver = RecipientResolver()
