import logging

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
        Build a dispatcher with standard wiring.
        """
        # 1. Map targets to publishers
        mapping = {}
        for pub in publishers:
            for target in DispatchTarget:
                if pub.supports_target(target):
                    mapping[target] = pub

        # 2. Critical targets (default: RabbitMQ)
        if critical_targets is None:
            critical_targets = {DispatchTarget.RABBITMQ}

        # 3. Build evaluator
        evaluator = DispatchEvaluator(critical_targets=critical_targets)

        # 4. Return composed dispatcher
        logger.info(f"🏗️ Dispatcher created with targets: {list(mapping.keys())}")
        return EventDispatcher(publishers_map=mapping, evaluator=evaluator)
