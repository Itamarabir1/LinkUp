from uuid import UUID

from .base import LinkupError


class AdminAccessRequiredError(LinkupError):
    """משתמש מחובר שאינו אדמין ניסה לגשת ל-`/api/v1/admin/*`."""

    status_code = 403
    error_code = "ADMIN_ACCESS_REQUIRED"
    message = "נדרשות הרשאות מנהל"


class OutboxEventNotFoundError(LinkupError):
    status_code = 404
    error_code = "ADMIN_OUTBOX_EVENT_NOT_FOUND"
    message = "אירוע Outbox לא נמצא"

    def __init__(self, event_id: UUID | str | None = None):
        payload = {"event_id": str(event_id)} if event_id is not None else None
        super().__init__(payload=payload)


class OutboxRequeueInvalidStatusError(LinkupError):
    status_code = 400
    error_code = "ADMIN_OUTBOX_REQUEUE_NOT_FAILED"
    message = "ניתן להחזיר לתור רק אירועים במצב FAILED"
