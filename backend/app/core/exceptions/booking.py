# app/core/exceptions/booking.py
"""שגיאות דומיין הזמנות ונהג/נוסע."""

from uuid import UUID

from .base import LinkupError


class RideNotAvailableError(LinkupError):
    """הנסיעה אינה פתוחה להצטרפות או לא נמצאה."""

    status_code = 404
    error_code = "BOOKING_RIDE_NOT_AVAILABLE"
    message = "הנסיעה אינה זמינה"

    def __init__(self, ride_id: int | None = None):
        payload = {"ride_id": ride_id} if ride_id is not None else None
        super().__init__(payload=payload)


class BookingAlreadyExistsError(LinkupError):
    """כבר קיימת בקשת הצטרפות לאותה נסיעה."""

    status_code = 400
    error_code = "BOOKING_ALREADY_EXISTS"
    message = "כבר ביקשת להצטרף לנסיעה הזו"

    def __init__(self, ride_id: int | None = None, request_id: int | None = None):
        payload = {}
        if ride_id is not None:
            payload["ride_id"] = ride_id
        if request_id is not None:
            payload["request_id"] = request_id
        super().__init__(payload=payload or None)


class PassengerRequestNotFoundError(LinkupError):
    """בקשת הנוסע לא נמצאה."""

    status_code = 404
    error_code = "BOOKING_REQUEST_NOT_FOUND"
    message = "בקשת הנוסע לא נמצאה"

    def __init__(self, request_id: int | None = None):
        payload = {"request_id": request_id} if request_id is not None else None
        super().__init__(payload=payload)


class BookingNotFoundError(LinkupError):
    """הזמנה לא נמצאה."""

    status_code = 404
    error_code = "BOOKING_NOT_FOUND"
    message = "הזמנה לא נמצאה"

    def __init__(self, booking_id: int | str | UUID | None = None):
        if booking_id is None:
            super().__init__()
            return
        bid = str(booking_id) if isinstance(booking_id, UUID) else booking_id
        super().__init__(payload={"booking_id": bid})


class NoSeatsAvailableError(LinkupError):
    """אין מקומות פנויים בנסיעה — בבקשה או באישור."""

    status_code = 409
    error_code = "NO_SEATS_AVAILABLE"
    message = "אין מקומות פנויים בנסיעה זו"

    def __init__(self, message: str = "אין מקומות פנויים בנסיעה זו"):
        super().__init__(message=message)


class ForbiddenRideActionError(LinkupError):
    """אין הרשאה לבצע פעולה על נסיעה/הזמנה זו."""

    status_code = 403
    error_code = "BOOKING_ACCESS_DENIED"
    message = "גישה חסומה"

    def __init__(self, detail: str | None = None):
        super().__init__(message=detail or self.message)
