"""
Generic in-memory circuit breaker (CLOSED / OPEN / HALF_OPEN).
Prometheus state gauge is injected per instance (geo, email, etc.).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from prometheus_client import Gauge

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
    state_gauge: Gauge
    failure_threshold: int = 5
    recovery_timeout: float = 60.0

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _opened_at: float | None = field(default=None, init=False)

    def allow_request(self) -> bool:
        try:
            if self._state == CircuitState.OPEN:
                if self._opened_at and (time.monotonic() - self._opened_at) >= self.recovery_timeout:
                    logger.info("CircuitBreaker[%s]: OPEN → HALF_OPEN", self.name)
                    self._state = CircuitState.HALF_OPEN
                    self.state_gauge.labels(name=self.name).set(1)
                    return True
                return False
            return True
        except Exception:
            return True  # fail open

    def record_success(self) -> None:
        try:
            if self._state != CircuitState.CLOSED:
                logger.info("CircuitBreaker[%s]: → CLOSED", self.name)
            self._state = CircuitState.CLOSED
            self.state_gauge.labels(name=self.name).set(0)
            self._failure_count = 0
            self._opened_at = None
        except Exception:
            pass

    def record_failure(self) -> None:
        try:
            self._failure_count += 1
            if self._state == CircuitState.HALF_OPEN or (self._failure_count >= self.failure_threshold):
                logger.warning(
                    "CircuitBreaker[%s]: → OPEN (%d failures)",
                    self.name,
                    self._failure_count,
                )
                self._state = CircuitState.OPEN
                self.state_gauge.labels(name=self.name).set(2)
                self._opened_at = time.monotonic()
        except Exception:
            pass

    @property
    def state_name(self) -> str:
        return self._state.value
