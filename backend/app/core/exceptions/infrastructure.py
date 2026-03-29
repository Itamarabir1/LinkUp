from typing import Any, Dict, Optional
from .base import LinkupError


class StorageServiceError(LinkupError):
    """תקלה בחיבור ל-S3"""

    status_code = 503
    error_code = "INFRA_STORAGE_ERROR"
    message = "שירות אחסון הקבצים אינו זמין כעת"

    def __init__(self, payload: Optional[Dict[str, Any]] = None):
        super().__init__(payload=payload)


class CacheConnectionError(LinkupError):
    """תקלה בחיבור ל-Redis"""

    status_code = 503
    error_code = "INFRA_REDIS_ERROR"
    message = "שגיאת חיבור לשירות הזיכרון (Redis)"

    def __init__(self, payload: Optional[Dict[str, Any]] = None):
        super().__init__(payload=payload)


class QueueServiceError(LinkupError):
    """תקלה בחיבור ל-RabbitMQ"""

    status_code = 503
    error_code = "INFRA_RABBIT_ERROR"
    message = "שגיאת חיבור לשירות ההודעות (RabbitMQ)"

    def __init__(self, payload: Optional[Dict[str, Any]] = None):
        super().__init__(payload=payload)


class RouteNotFoundError(LinkupError):
    """נזרקת כאשר לא נמצא מסלול בין שתי נקודות."""

    status_code = 404
    error_code = "GEO_ROUTE_NOT_FOUND"
    message = "לא נמצא מסלול בין המיקומים שנבחרו"

    def __init__(self, origin: str, destination: str):
        super().__init__(
            message=f"לא נמצא מסלול נסיעה בין {origin} ל-{destination}.",
            payload={"origin": origin, "destination": destination},
        )


class GeocodingError(LinkupError):
    status_code = 422
    error_code = "GEO_ADDRESS_NOT_RESOLVED"
    message = "לא הצלחנו לאתר את הכתובת המבוקשת"

    def __init__(self, address: Optional[str] = None):
        super().__init__(
            message=self.message,
            status_code=self.status_code,
            error_code=self.error_code,
            payload={"address": address} if address else None,
        )


class InfrastructureError(LinkupError):
    """שגיאות תשתית: Redis, DB, Network, וכו'."""

    status_code = 503
    error_code = "INFRA_ERROR"

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        payload = {"detail": detail} if detail else None
        super().__init__(
            message=message, error_code=error_code or self.error_code, payload=payload
        )


class RateLimitExceeded(LinkupError):
    """יותר מדי בקשות — לקוח יכול לקרוא retry_after מ-details."""

    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "יותר מדי בקשות, נסה שוב בעוד מעט"

    def __init__(self, retry_after: int = 60):
        super().__init__(payload={"retry_after": retry_after})


class S3UploadFailed(LinkupError):
    status_code = 502
    error_code = "S3_UPLOAD_FAILED"
    message = "העלאת הקובץ לשירות האחסון נכשלה"


class S3DeleteFailed(LinkupError):
    status_code = 502
    error_code = "S3_DELETE_FAILED"
    message = "מחיקת הקובץ מהאחסון נכשלה"


class RedisUnavailable(LinkupError):
    status_code = 503
    error_code = "REDIS_UNAVAILABLE"
    message = "שירות הזיכרון (Redis) אינו זמין כרגע"


class WorkerTaskFailed(LinkupError):
    status_code = 500
    error_code = "WORKER_TASK_FAILED"
    message = "משימת רקע נכשלה"


class ExternalServiceError(LinkupError):
    """כשל בקריאה לשירות חיצוני (מייל, מפות, OAuth provider, וכו')."""

    status_code = 502
    error_code = "EXTERNAL_SERVICE_ERROR"
    message = "שירות חיצוני אינו זמין או החזיר שגיאה"
