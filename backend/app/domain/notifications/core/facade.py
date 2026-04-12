import logging
from typing import Any

from app.core.exceptions.base import LinkupError
from app.domain.notifications.constants import NotificationEvent

from .builders.registry import CONTEXT_MAP

logger = logging.getLogger(__name__)


class NotificationContextFacade:
    @classmethod
    def get_context(cls, event_key: NotificationEvent, data: Any) -> dict[str, Any]:
        config = CONTEXT_MAP.get(event_key)
        if not config:
            raise LinkupError(f"No configuration for event: {event_key}")

        builder = config["builder"]
        schema = config["schema"]

        # Validate: use Pydantic schema when present; otherwise pass data through
        processed_data = data
        if schema and isinstance(data, dict):
            processed_data = schema(**data)

        try:
            # Run builder.build (uses BaseBuilder)
            return builder.build(processed_data, str(event_key))
        except Exception as e:
            logger.error(f"❌ Builder failed for {event_key}: {e}", exc_info=True)
            raise LinkupError(f"Context construction failed for {event_key}")
