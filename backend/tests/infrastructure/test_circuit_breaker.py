"""Unit tests for generic CircuitBreaker (isolated Prometheus registry)."""

from __future__ import annotations

import time

import pytest
from prometheus_client import CollectorRegistry, Gauge

from app.infrastructure.circuit_breaker import CircuitBreaker


@pytest.fixture()
def breaker() -> CircuitBreaker:
    reg = CollectorRegistry()
    g = Gauge("test_circuit_breaker_state", "test", ["name"], registry=reg)
    return CircuitBreaker(
        name="test_cb",
        state_gauge=g,
        failure_threshold=3,
        recovery_timeout=0.05,
    )


def test_allow_request_when_closed(breaker: CircuitBreaker) -> None:
    assert breaker.allow_request() is True
    assert breaker.state_name == "closed"


def test_opens_after_failure_threshold(breaker: CircuitBreaker) -> None:
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.allow_request() is True
    assert breaker.state_name == "closed"
    breaker.record_failure()
    assert breaker.state_name == "open"
    assert breaker.allow_request() is False


def test_half_open_after_recovery_timeout(breaker: CircuitBreaker) -> None:
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    assert breaker.state_name == "open"
    assert breaker.allow_request() is False
    time.sleep(0.06)
    assert breaker.allow_request() is True
    assert breaker.state_name == "half_open"


def test_record_success_closes_from_half_open(breaker: CircuitBreaker) -> None:
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    time.sleep(0.06)
    assert breaker.allow_request() is True
    assert breaker.state_name == "half_open"
    breaker.record_success()
    assert breaker.state_name == "closed"


def test_failure_in_half_open_reopens(breaker: CircuitBreaker) -> None:
    breaker.record_failure()
    breaker.record_failure()
    breaker.record_failure()
    time.sleep(0.06)
    assert breaker.allow_request() is True
    breaker.record_failure()
    assert breaker.state_name == "open"
