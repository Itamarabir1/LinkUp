from uuid import UUID

from .base import LinkupError


class ActiveBookingExistsError(LinkupError):
    message = "כבר יש לך נסיעה פעילה"
    status_code = 409
    error_code = "PSG_ACTIVE_BOOKING"

    def __init__(self, ride_id: int | str | UUID | None = None):
        payload: dict = {}
        if ride_id is not None:
            payload["ride_id"] = str(ride_id)
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
            payload=payload or None,
        )


class InsufficientPermissionsForRide(LinkupError):
    message = "אין לך הרשאה לגשת לנסיעה זו"
    status_code = 403
    error_code = "PSG_RIDE_ACCESS_DENIED"

    def __init__(
        self,
        ride_id: int | str | UUID | None = None,
        reason: str | None = None,
    ):
        msg = self.message
        if reason:
            msg = f"{self.message} — {reason}"
        payload: dict = {}
        if ride_id is not None:
            payload["ride_id"] = str(ride_id)
        if reason is not None:
            payload["reason"] = reason
        super().__init__(
            message=msg,
            status_code=self.status_code,
            error_code=self.error_code,
            payload=payload or None,
        )
