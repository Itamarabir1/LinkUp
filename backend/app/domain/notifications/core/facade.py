import logging
from typing import Any, Dict

from app.core.exceptions.base import LinkupError

from .builders.registry import CONTEXT_MAP
from app.domain.notifications.constants import NotificationEvent

logger = logging.getLogger(__name__)


class NotificationContextFacade:
    @classmethod
    def get_context(cls, event_key: NotificationEvent, data: Any) -> Dict[str, Any]:
        config = CONTEXT_MAP.get(event_key)
        if not config:
            raise LinkupError(f"No configuration for event: {event_key}")

        builder = config["builder"]
        schema = config["schema"]

        # ולידציה: אם יש סכמה, נשתמש בה. אם לא, נעביר את האובייקט כמו שהוא.
        processed_data = data
        if schema and isinstance(data, dict):
            processed_data = schema(**data)

        try:
            # הפעלת ה-build (שנשען על ה-BaseBuilder המצוין שלך)
            return builder.build(processed_data, str(event_key))
        except Exception as e:
            logger.error(f"❌ Builder failed for {event_key}: {e}", exc_info=True)
            raise LinkupError(f"Context construction failed for {event_key}")
