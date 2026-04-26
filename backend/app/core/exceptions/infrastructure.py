from typing import Any

from .base import LinkUpError


class StorageServiceError(LinkUpError):
    """S3 / object storage connectivity failure."""

    status_code = 503
    error_code = "INFRA_STORAGE_ERROR"
    message = "שירות אחסון הקבצים אינו זמין כעת"

    def __init__(self, payload: dict[str, Any] | None = None):
        super().__init__(payload=payload)


class CacheConnectionError(LinkUpError):
    """Redis connectivity failure."""

    status_code = 503
    error_code = "INFRA_REDIS_ERROR"
    message = "שגיאת חיבור לשירות הזיכרון (Redis)"

    def __init__(self, payload: dict[str, Any] | None = None):
        super().__init__(payload=payload)


class QueueServiceError(LinkUpError):
    """RabbitMQ connectivity failure."""

    status_code = 503
    error_code = "INFRA_RABBIT_ERROR"
    message = "שגיאת חיבור לשירות ההודעות (RabbitMQ)"

    def __init__(self, payload: dict[str, Any] | None = None):
        super().__init__(payload=payload)


class RouteNotFoundError(LinkUpError):
    """No driving route found between origin and destination."""

    status_code = 404
    error_code = "GEO_ROUTE_NOT_FOUND"
    message = "לא נמצא מסלול בין המיקומים שנבחרו"

    def __init__(self, origin: str, destination: str):
        super().__init__(
            message=f"לא נמצא מסלול נסיעה בין {origin} ל-{destination}.",
            payload={"origin": origin, "destination": destination},
        )


class GeocodingError(LinkUpError):
    status_code = 422
    error_code = "GEO_ADDRESS_NOT_RESOLVED"
    message = "לא הצלחנו לאתר את הכתובת המבוקשת"

    def __init__(self, address: str | None = None):
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
            payload={"address": address} if address else None,
        )


class InfrastructureError(LinkUpError):
    """Generic infrastructure failure (cache, DB, network, etc.)."""

    status_code = 503
    error_code = "INFRA_ERROR"

    def __init__(
        self,
        message: str,
        detail: str | None = None,
        error_code: str | None = None,
    ):
        payload = {"detail": detail} if detail else None
        super().__init__(message=message, error_code=error_code or self.error_code, payload=payload)


class RateLimitExceeded(LinkUpError):
    """Too many requests; clients may read retry_after from payload.

    The optional ``limit`` and ``remaining`` carry standard rate-limit metadata
    so the central error handler can emit ``X-RateLimit-Limit`` /
    ``X-RateLimit-Remaining`` / ``X-RateLimit-Reset`` headers (Stripe / GitHub
    convention).
    """

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "יותר מדי בקשות, נסה שוב בעוד מעט"

    def __init__(
        self,
        retry_after: int = 60,
        *,
        limit: int | None = None,
        remaining: int | None = None,
    ):
        payload: dict[str, Any] = {"retry_after": retry_after}
        if limit is not None:
            payload["limit"] = limit
        if remaining is not None:
            payload["remaining"] = remaining
        super().__init__(payload=payload)


class S3UploadFailed(LinkUpError):
    status_code = 502
    error_code = "S3_UPLOAD_FAILED"
    message = "העלאת הקובץ לשירות האחסון נכשלה"


class S3DeleteFailed(LinkUpError):
    status_code = 502
    error_code = "S3_DELETE_FAILED"
    message = "מחיקת הקובץ מהאחסון נכשלה"


class RedisUnavailable(LinkUpError):
    status_code = 503
    error_code = "REDIS_UNAVAILABLE"
    message = "שירות הזיכרון (Redis) אינו זמין כרגע"


class WorkerTaskFailed(LinkUpError):
    status_code = 500
    error_code = "WORKER_TASK_FAILED"
    message = "משימת רקע נכשלה"


class ExternalServiceError(LinkUpError):
    """Third-party dependency failed (email, maps, OAuth, etc.)."""

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    message = "שירות חיצוני אינו זמין או החזיר שגיאה"


class InternalServerError(LinkUpError):
    status_code = 500
    error_code = "INTERNAL_ERROR"
    message = "שגיאת שרת פנימית"

    def __init__(self, message: str | None = None):
        super().__init__(message=message if message is not None else InternalServerError.message)
