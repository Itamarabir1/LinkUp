"""
מקור אמת יחיד לפרסום אירועים מהדומיין.
הדומיין לא יודע על RabbitMQ או EventDispatcher – רק כותב ל-Outbox באותה טרנזקציה.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.events.enum import DispatchTarget
from app.infrastructure.outbox.model import OutboxEvent
from app.infrastructure.outbox.repository import OutboxRepository

_outbox_repo = OutboxRepository()


async def publish_to_outbox(
    db: AsyncSession,
    event_name: str,
    payload: dict[str, Any],
    targets: list[str] | None = None,
) -> None:
    """
    כותב אירוע ל-Outbox באותה טרנזקציה.
    ה-Worker יקרא מאוחר יותר וישלח ל-RabbitMQ וכו'.
    """
    if targets is None:
        targets = [DispatchTarget.RABBITMQ.value]
    event = OutboxEvent(
        event_name=event_name,
        payload=payload,
        targets=targets,
    )
    await _outbox_repo.save_event(db, event)
