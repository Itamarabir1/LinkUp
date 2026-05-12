"""
Notification error hierarchy — drives retry/DLQ decisions at the RabbitMQ consumer layer.

TransientNotificationError  → nack → broker retry queue → re-deliver after TTL
PermanentNotificationError  → log & swallow → message acked (no retry)
"""


class NotificationError(Exception):
    """Base for all notification-domain errors."""


class TransientNotificationError(NotificationError):
    """Retryable — network timeout, rate limit, temporary service outage."""


class PermanentNotificationError(NotificationError):
    """Non-retryable — invalid token, bad template, permanently rejected recipient."""
