"""Brevo transactional email circuit breaker."""

from __future__ import annotations

from app.infrastructure.circuit_breaker import CircuitBreaker
from app.infrastructure.metrics import brevo_circuit_breaker_state

brevo_email_cb = CircuitBreaker(
    name="brevo_email",
    state_gauge=brevo_circuit_breaker_state,
    failure_threshold=5,
    recovery_timeout=60.0,
)
