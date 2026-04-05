import logging
from typing import List, Optional, Set

from app.domain.events.enum import DispatchTarget
from app.infrastructure.events.publishers.base import EventPublisher

from .base import EventDispatcher
from .evaluator import DispatchEvaluator

logger = logging.getLogger(__name__)


class DispatcherFactory:
    @staticmethod
    def create_standard_dispatcher(
        publishers: list[EventPublisher],
        critical_targets: set[DispatchTarget] | None = None,
    ) -> EventDispatcher:
        """
        בונה Dispatcher עם הגדרות סטנדרטיות.
        """
        # 1. מיפוי פבלישרים
        mapping = {}
        for pub in publishers:
            for target in DispatchTarget:
                if pub.supports_target(target):
                    mapping[target] = pub

        # 2. הגדרת יעדים קריטיים (ברירת מחדל היא RabbitMQ אם לא הוגדר אחרת)
        if critical_targets is None:
            critical_targets = {DispatchTarget.RABBITMQ}

        # 3. יצירת ה-Evaluator
        evaluator = DispatchEvaluator(critical_targets=critical_targets)

        # 4. החזרת הדיספאצ'ר המורכב
        logger.info(f"🏗️ Dispatcher created with targets: {list(mapping.keys())}")
        return EventDispatcher(publishers_map=mapping, evaluator=evaluator)
