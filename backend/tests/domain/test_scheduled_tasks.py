"""Unit tests for scheduled tasks (publisher + consumer dispatcher)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.events.routing import (
    ROUTING_KEY_CHAT_TIMEOUT,
    ROUTING_KEY_FUEL_SCAN,
    ROUTING_KEY_MAINTENANCE,
    ROUTING_KEY_REMINDERS,
    SCHEDULED_EXCHANGE,
)
from app.workers.tasks.fuel_price_task import FUEL_SCAN_INTERVAL
from app.workers.tasks.scheduled_tasks import (
    CHECK_INTERVAL,
    INTERVAL_CHAT_TIMEOUT,
    INTERVAL_MAINTENANCE,
    INTERVAL_REMINDERS,
    handle_scheduled_task,
    run_scheduled_tasks_publisher,
)


# ============================================================
# handle_scheduled_task (consumer dispatcher)
# ============================================================


@pytest.mark.asyncio
async def test_handle_scheduled_task_dispatches_fuel_scan():
    with patch(
        "app.workers.tasks.scheduled_tasks.execute_fuel_scan_job",
        new_callable=AsyncMock,
    ) as mock_job:
        await handle_scheduled_task({"trigger": "fuel_scan"}, ROUTING_KEY_FUEL_SCAN)

    mock_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_scheduled_task_dispatches_maintenance():
    with patch(
        "app.workers.tasks.scheduled_tasks.execute_maintenance_job",
        new_callable=AsyncMock,
    ) as mock_job:
        await handle_scheduled_task({"trigger": "maintenance"}, ROUTING_KEY_MAINTENANCE)

    mock_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_scheduled_task_dispatches_reminders():
    with patch(
        "app.workers.tasks.scheduled_tasks.execute_reminders_job",
        new_callable=AsyncMock,
    ) as mock_job:
        await handle_scheduled_task({"trigger": "reminders"}, ROUTING_KEY_REMINDERS)

    mock_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_scheduled_task_dispatches_chat_timeout():
    with patch(
        "app.workers.tasks.scheduled_tasks.execute_chat_timeout_job",
        new_callable=AsyncMock,
    ) as mock_job:
        await handle_scheduled_task({"trigger": "chat_timeout"}, ROUTING_KEY_CHAT_TIMEOUT)

    mock_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_scheduled_task_unknown_routing_key_does_not_raise():
    await handle_scheduled_task({"trigger": "unknown"}, "some.unknown.key")


@pytest.mark.asyncio
async def test_handle_scheduled_task_exception_is_caught_and_logged():
    with patch(
        "app.workers.tasks.scheduled_tasks.execute_fuel_scan_job",
        new_callable=AsyncMock,
        side_effect=RuntimeError("fuel API down"),
    ):
        await handle_scheduled_task({"trigger": "fuel_scan"}, ROUTING_KEY_FUEL_SCAN)


# ============================================================
# run_scheduled_tasks_publisher
# ============================================================


@pytest.mark.asyncio
async def test_publisher_publishes_all_tasks_on_first_iteration():
    """After enough time has elapsed, all scheduled messages should be published."""
    rabbitmq_client = AsyncMock()
    rabbitmq_client.publish = AsyncMock()

    iteration_count = {"n": 0}

    async def fake_sleep(seconds):
        iteration_count["n"] += 1
        if iteration_count["n"] >= 1:
            raise asyncio.CancelledError()

    elapsed = FUEL_SCAN_INTERVAL + 1

    with patch("app.workers.tasks.scheduled_tasks.asyncio.sleep", side_effect=fake_sleep), patch(
        "app.workers.tasks.scheduled_tasks.time.monotonic",
        side_effect=[0, elapsed],
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_scheduled_tasks_publisher(rabbitmq_client)

    assert rabbitmq_client.publish.await_count == 4

    call_routing_keys = [
        call.args[1] for call in rabbitmq_client.publish.call_args_list
    ]
    assert ROUTING_KEY_CHAT_TIMEOUT in call_routing_keys
    assert ROUTING_KEY_REMINDERS in call_routing_keys
    assert ROUTING_KEY_MAINTENANCE in call_routing_keys
    assert ROUTING_KEY_FUEL_SCAN in call_routing_keys


@pytest.mark.asyncio
async def test_publisher_uses_scheduled_exchange():
    rabbitmq_client = AsyncMock()
    rabbitmq_client.publish = AsyncMock()

    async def fake_sleep(seconds):
        raise asyncio.CancelledError()

    elapsed = FUEL_SCAN_INTERVAL + 1

    with patch("app.workers.tasks.scheduled_tasks.asyncio.sleep", side_effect=fake_sleep), patch(
        "app.workers.tasks.scheduled_tasks.time.monotonic",
        side_effect=[0, elapsed],
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_scheduled_tasks_publisher(rabbitmq_client)

    assert rabbitmq_client.publish.await_count == 4
    for call in rabbitmq_client.publish.call_args_list:
        assert call.args[2] == SCHEDULED_EXCHANGE


@pytest.mark.asyncio
async def test_publisher_skips_tasks_not_yet_due():
    """When not enough time has elapsed, tasks should not be published."""
    rabbitmq_client = AsyncMock()
    rabbitmq_client.publish = AsyncMock()

    async def fake_sleep(seconds):
        raise asyncio.CancelledError()

    with patch("app.workers.tasks.scheduled_tasks.asyncio.sleep", side_effect=fake_sleep), patch(
        "app.workers.tasks.scheduled_tasks.time.monotonic",
        side_effect=[0, 10],
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_scheduled_tasks_publisher(rabbitmq_client)

    rabbitmq_client.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_publisher_exception_does_not_crash_loop():
    """A publish error should be caught; the loop continues to the next sleep."""
    rabbitmq_client = AsyncMock()
    rabbitmq_client.publish = AsyncMock(side_effect=RuntimeError("connection lost"))

    call_count = {"n": 0}

    async def fake_sleep(seconds):
        call_count["n"] += 1
        if call_count["n"] >= 2:
            raise asyncio.CancelledError()

    elapsed = FUEL_SCAN_INTERVAL + 1

    with patch("app.workers.tasks.scheduled_tasks.asyncio.sleep", side_effect=fake_sleep), patch(
        "app.workers.tasks.scheduled_tasks.time.monotonic",
        side_effect=[0, elapsed, elapsed + 1],
    ):
        with pytest.raises(asyncio.CancelledError):
            await run_scheduled_tasks_publisher(rabbitmq_client)

    assert call_count["n"] >= 1
