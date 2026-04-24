from __future__ import annotations

import asyncio
import json
import logging
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.rabbitmq.consumer import RabbitMQConsumer, get_retry_count_from_xdeath
from app.infrastructure.rabbitmq.dlq_monitor import _queue_message_count, run_dlq_monitor


def test_get_retry_count_from_xdeath_queue_scoped() -> None:
    headers = {
        "x-death": [
            {"queue": "notifications_queue", "count": 2},
            {"queue": "other_queue", "count": 9},
            {"queue": "notifications_queue", "count": 1},
        ]
    }
    assert get_retry_count_from_xdeath(headers, "notifications_queue") == 3


def test_queue_message_count_handles_invalid_values() -> None:
    class _Decl:
        def __init__(self, count):
            self.message_count = count

    class _Queue:
        def __init__(self, count):
            self.declaration_result = _Decl(count)

    assert _queue_message_count(_Queue("12")) == 12
    assert _queue_message_count(_Queue("x")) == 0


@pytest.mark.asyncio
async def test_handle_with_retry_terminal_path_publishes_to_dlq_exchange() -> None:
    consumer = RabbitMQConsumer(rabbit_client=object(), queue_name="notifications_queue")
    consumer._dlq_exchange = AsyncMock()

    message = AsyncMock()
    message.headers = {"x-death": [{"queue": "notifications_queue", "count": 3}]}
    message.body = json.dumps({"foo": "bar"}).encode()
    message.routing_key = "notifications.event"
    message.ack = AsyncMock()
    message.nack = AsyncMock()

    async def _failing_callback(payload, routing_key):
        raise RuntimeError("boom")

    await consumer._handle_with_retry(message, _failing_callback, "notifications_queue")

    consumer._dlq_exchange.publish.assert_awaited_once()
    message.ack.assert_awaited_once()
    message.nack.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_with_retry_transient_path_nacks_for_broker_retry() -> None:
    consumer = RabbitMQConsumer(rabbit_client=object(), queue_name="notifications_queue")
    consumer._dlq_exchange = AsyncMock()

    message = AsyncMock()
    message.headers = {"x-death": [{"queue": "notifications_queue", "count": 1}]}
    message.body = json.dumps({"foo": "bar"}).encode()
    message.routing_key = "notifications.event"
    message.ack = AsyncMock()
    message.nack = AsyncMock()

    async def _failing_callback(payload, routing_key):
        raise RuntimeError("transient")

    await consumer._handle_with_retry(message, _failing_callback, "notifications_queue")

    message.nack.assert_awaited_once_with(requeue=False)
    message.ack.assert_not_awaited()
    consumer._dlq_exchange.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_dlq_monitor_emits_threshold_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    class _Decl:
        def __init__(self, count: int):
            self.message_count = count

    class _Queue:
        def __init__(self, count: int):
            self.declaration_result = _Decl(count)

    stop_event = asyncio.Event()

    async def _declare_queue(queue_name: str, durable: bool, passive: bool):
        stop_event.set()
        return _Queue(55)

    fake_channel = AsyncMock()
    fake_channel.declare_queue = AsyncMock(side_effect=_declare_queue)

    fake_client = AsyncMock()
    fake_client.get_consumer_channel = AsyncMock(return_value=fake_channel)

    monkeypatch.setattr("app.infrastructure.rabbitmq.dlq_monitor._retryable_dlq_names", lambda: ["notifications_queue.dlq"])
    monkeypatch.setattr("app.infrastructure.rabbitmq.dlq_monitor.DLQ_MONITOR_INTERVAL_SECONDS", 0)

    caplog.set_level(logging.CRITICAL)
    await run_dlq_monitor(fake_client, stop_event)

    assert "DLQ depth critical queue=notifications_queue.dlq depth=55" in caplog.text
