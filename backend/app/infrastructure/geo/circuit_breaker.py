"""
Circuit Breaker for external Google Maps API calls.
In-memory, asyncio-safe, singleton per service.

States:
  CLOSED    → normal operation
  OPEN      → failing fast (no calls to Google)
  HALF_OPEN → testing recovery (one request allowed)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    name: str
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
                self._opened_at = time.monotonic()
        except Exception:
            pass

    @property
    def state_name(self) -> str:
        return self._state.value


# Singletons — one per Google API
google_geocoding_cb = CircuitBreaker(
    name="google_geocoding",
    failure_threshold=5,
    recovery_timeout=60.0,
)
google_directions_cb = CircuitBreaker(
    name="google_directions",
    failure_threshold=5,
    recovery_timeout=60.0,
)
google_distance_matrix_cb = CircuitBreaker(
    name="google_distance_matrix",
    failure_threshold=5,
    recovery_timeout=60.0,
)
