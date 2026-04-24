from dataclasses import dataclass

from app.domain.events.routing import (
    AVATAR_UPLOAD_EXCHANGES,
    NOTIFICATION_EXCHANGES,
    SCHEDULED_EXCHANGES,
    SCHEDULED_TASKS_QUEUE,
)


@dataclass(frozen=True)
class QueueSpec:
    queue_name: str
    exchange_names: tuple[str, ...]
    retry_enabled: bool
    retry_delay_ms: int = 30000
    max_retries: int = 3
    prefetch_count: int = 10
    durable: bool = True


QUEUE_SPECS: dict[str, QueueSpec] = {
    "notifications_queue": QueueSpec(
        queue_name="notifications_queue",
        exchange_names=tuple(NOTIFICATION_EXCHANGES),
        retry_enabled=True,
    ),
    "avatar_upload_queue": QueueSpec(
        queue_name="avatar_upload_queue",
        exchange_names=tuple(AVATAR_UPLOAD_EXCHANGES),
        retry_enabled=True,
    ),
    SCHEDULED_TASKS_QUEUE: QueueSpec(
        queue_name=SCHEDULED_TASKS_QUEUE,
        exchange_names=tuple(SCHEDULED_EXCHANGES),
        retry_enabled=False,
    ),
}


def get_queue_spec(queue_name: str, exchange_names_override: list[str] | None = None) -> QueueSpec:
    """
    Returns centralized queue topology config.
    Optional exchange override preserves backward compatibility for callers.
    """
    spec = QUEUE_SPECS.get(
        queue_name,
        QueueSpec(
            queue_name=queue_name,
            exchange_names=tuple(exchange_names_override or ("system_events",)),
            retry_enabled=False,
        ),
    )
    if exchange_names_override is None:
        return spec
    return QueueSpec(
        queue_name=spec.queue_name,
        exchange_names=tuple(exchange_names_override),
        retry_enabled=spec.retry_enabled,
        retry_delay_ms=spec.retry_delay_ms,
        max_retries=spec.max_retries,
        prefetch_count=spec.prefetch_count,
        durable=spec.durable,
    )
