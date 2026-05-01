"""
Google Maps API circuit breakers — singletons using geo_circuit_breaker_state.
"""

from __future__ import annotations

from app.infrastructure.circuit_breaker import CircuitBreaker
from app.infrastructure.metrics import geo_circuit_breaker_state

# Singletons — one per Google API
google_geocoding_cb = CircuitBreaker(
    name="google_geocoding",
    state_gauge=geo_circuit_breaker_state,
    failure_threshold=5,
    recovery_timeout=60.0,
)
google_directions_cb = CircuitBreaker(
    name="google_directions",
    state_gauge=geo_circuit_breaker_state,
    failure_threshold=5,
    recovery_timeout=60.0,
)
google_distance_matrix_cb = CircuitBreaker(
    name="google_distance_matrix",
    state_gauge=geo_circuit_breaker_state,
    failure_threshold=5,
    recovery_timeout=60.0,
)
