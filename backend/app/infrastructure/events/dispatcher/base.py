import logging
from typing import Dict

from app.domain.events.enum import DispatchTarget
from app.domain.events.schema import Event
from app.infrastructure.events.publishers.base import EventPublisher

from .evaluator import DispatchEvaluator

logger = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(
        self,
        publishers_map: dict[DispatchTarget, EventPublisher],
        evaluator: DispatchEvaluator,
    ):
        self._publishers = publishers_map
        self._evaluator = evaluator

    async def dispatch(self, event: Event) -> dict[DispatchTarget, bool]:
        results = {}
        errors = []

        for target in event.targets:
            publisher = self._publishers.get(target)

            if not publisher:
                logger.warning(f"⚠️ No publisher registered for target: {target}")
                results[target] = False
                continue

            try:
                success = await publisher.publish(event)
                results[target] = success
                if not success:
                    errors.append((target, "Publisher returned False"))
            except Exception as e:
                results[target] = False
                errors.append((target, str(e)))
                logger.error(f"❌ Failed dispatching {event.name} to {target}: {e}")

        # העברת האחריות לבדיקת התוצאות ל-Evaluator
        self._evaluator.evaluate(event, results, errors)

        return results
