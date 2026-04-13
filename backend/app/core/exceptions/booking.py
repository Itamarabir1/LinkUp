# app/core/exceptions/booking.py
"""Booking / ride-participation domain errors."""

from uuid import UUID

from .base import LinkupError


class RideNotAvailableError(LinkupError):
    """Ride is not open for joins or was not found."""

    status_code = 404
    error_code = "BOOKING_RIDE_NOT_AVAILABLE"
    message = "הנסיעה אינה זמינה"

    def __init__(self, ride_id: int | None = None):
        payload = {"ride_id": ride_id} if ride_id is not None else None
        super().__init__(payload=payload)


class BookingAlreadyExistsError(LinkupError):
    """Passenger already has a join request for this ride."""

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
    """Passenger request id does not exist."""

    status_code = 404
    error_code = "BOOKING_REQUEST_NOT_FOUND"
    message = "בקשת הנוסע לא נמצאה"

    def __init__(self, request_id: int | None = None):
        payload = {"request_id": request_id} if request_id is not None else None
        super().__init__(payload=payload)


class BookingNotFoundError(LinkupError):
    """Booking id does not exist."""

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
    """No free seats on the ride (request or approval flow)."""

    status_code = 409
    error_code = "NO_SEATS_AVAILABLE"
    message = "אין מקומות פנויים בנסיעה זו"

    def __init__(self, message: str = "אין מקומות פנויים בנסיעה זו"):
        super().__init__(message=message)


class ForbiddenRideActionError(LinkupError):
    """Caller may not perform this action on the ride or booking."""

    status_code = 403
    error_code = "BOOKING_ACCESS_DENIED"
    message = "גישה חסומה"

    def __init__(self, detail: str | None = None):
        super().__init__(message=detail or self.message)
