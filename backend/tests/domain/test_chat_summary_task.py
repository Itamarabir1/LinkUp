"""Unit tests for chat summary (completion) task — Redis listener + message processor."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from app.core.exceptions.infrastructure import WorkerTaskFailed
from app.workers.tasks.chat_summary_task import (
    CHAT_COMPLETION_PATTERN,
    _process_completion_message,
    run_chat_completion_redis_listener,
)


# ============================================================
# _process_completion_message
# ============================================================


@pytest.mark.asyncio
async def test_process_completion_missing_conversation_id_raises():
    payload = json.dumps({"trigger_user_id": str(uuid4())})
    with pytest.raises(WorkerTaskFailed):
        await _process_completion_message(payload)


@pytest.mark.asyncio
async def test_process_completion_missing_trigger_user_id_raises():
    payload = json.dumps({"conversation_id": str(uuid4())})
    with pytest.raises(WorkerTaskFailed):
        await _process_completion_message(payload)


@pytest.mark.asyncio
async def test_process_completion_invalid_json_raises():
    with pytest.raises(WorkerTaskFailed):
        await _process_completion_message("not valid json {{{")


@pytest.mark.asyncio
async def test_process_completion_happy_path_calls_handle_conversation_completion():
    conversation_id = uuid4()
    trigger_user_id = uuid4()
    payload = json.dumps({
        "conversation_id": str(conversation_id),
        "trigger_user_id": str(trigger_user_id),
    })

    with patch(
        "app.workers.tasks.chat_summary_task.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.chat_summary_task.handle_conversation_completion",
        new_callable=AsyncMock,
    ) as mock_handler:
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await _process_completion_message(payload)

    mock_handler.assert_awaited_once_with(mock_db, conversation_id, trigger_user_id)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_completion_db_error_triggers_rollback_and_raises():
    conversation_id = uuid4()
    trigger_user_id = uuid4()
    payload = json.dumps({
        "conversation_id": str(conversation_id),
        "trigger_user_id": str(trigger_user_id),
    })

    with patch(
        "app.workers.tasks.chat_summary_task.SessionLocal",
    ) as mock_session_cls, patch(
        "app.workers.tasks.chat_summary_task.handle_conversation_completion",
        new_callable=AsyncMock,
        side_effect=RuntimeError("AI service unavailable"),
    ):
        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(WorkerTaskFailed):
            await _process_completion_message(payload)

    mock_db.rollback.assert_awaited_once()


# ============================================================
# run_chat_completion_redis_listener
# ============================================================


@pytest.mark.asyncio
async def test_listener_subscribes_to_correct_pattern():
    stop_event = asyncio.Event()
    stop_event.set()

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ):
        await run_chat_completion_redis_listener(stop_event)

    mock_pubsub.psubscribe.assert_awaited_once_with(CHAT_COMPLETION_PATTERN)
    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_listener_processes_pmessage():
    stop_event = asyncio.Event()
    conversation_id = uuid4()
    trigger_user_id = uuid4()
    payload_data = json.dumps({
        "conversation_id": str(conversation_id),
        "trigger_user_id": str(trigger_user_id),
    })

    call_count = {"n": 0}

    async def get_message_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "type": "pmessage",
                "pattern": CHAT_COMPLETION_PATTERN,
                "channel": f"chat:completion:{conversation_id}",
                "data": payload_data,
            }
        stop_event.set()
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(side_effect=get_message_side_effect)

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ), patch(
        "app.workers.tasks.chat_summary_task._process_completion_message",
        new_callable=AsyncMock,
    ) as mock_process:
        await run_chat_completion_redis_listener(stop_event)

    mock_process.assert_awaited_once_with(payload_data)


@pytest.mark.asyncio
async def test_listener_ignores_non_pmessage_types():
    stop_event = asyncio.Event()
    call_count = {"n": 0}

    async def get_message_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"type": "subscribe", "pattern": None, "channel": None, "data": None}
        stop_event.set()
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(side_effect=get_message_side_effect)

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ), patch(
        "app.workers.tasks.chat_summary_task._process_completion_message",
        new_callable=AsyncMock,
    ) as mock_process:
        await run_chat_completion_redis_listener(stop_event)

    mock_process.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_handles_timeout_gracefully():
    stop_event = asyncio.Event()
    call_count = {"n": 0}

    async def get_message_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutError()
        stop_event.set()
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(side_effect=get_message_side_effect)

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ):
        await run_chat_completion_redis_listener(stop_event)

    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_listener_handles_processing_error_and_continues():
    stop_event = asyncio.Event()
    call_count = {"n": 0}
    payload_data = json.dumps({
        "conversation_id": str(uuid4()),
        "trigger_user_id": str(uuid4()),
    })

    async def get_message_side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "type": "pmessage",
                "pattern": CHAT_COMPLETION_PATTERN,
                "channel": "chat:completion:xyz",
                "data": payload_data,
            }
        stop_event.set()
        return None

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(side_effect=get_message_side_effect)

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ), patch(
        "app.workers.tasks.chat_summary_task._process_completion_message",
        new_callable=AsyncMock,
        side_effect=WorkerTaskFailed(),
    ):
        await run_chat_completion_redis_listener(stop_event)

    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_listener_closes_client_on_cancellation():
    stop_event = asyncio.Event()

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock(side_effect=asyncio.CancelledError())

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ):
        await run_chat_completion_redis_listener(stop_event)

    mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_listener_closes_client_on_redis_connection_error():
    stop_event = asyncio.Event()

    mock_pubsub = AsyncMock()
    mock_pubsub.psubscribe = AsyncMock(side_effect=ConnectionError("Redis unreachable"))

    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.close = AsyncMock()

    with patch(
        "app.workers.tasks.chat_summary_task.redis.from_url",
        return_value=mock_client,
    ):
        await run_chat_completion_redis_listener(stop_event)

    mock_client.close.assert_awaited_once()
