"""Router idempotency for POST conversation messages (Redis contract)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.chat import router as chat_router_module
from app.domain.chat.schema import MessageCreate, MessageResponse
from app.domain.users.model import User


@pytest.mark.asyncio
async def test_post_message_leader_calls_set_result(monkeypatch, db_session):
    conv_id = uuid4()
    sender_id = uuid4()

    dummy_user = MagicMock(spec=User)
    dummy_user.user_id = sender_id

    sent = MessageResponse(
        message_id=99,
        conversation_id=conv_id,
        sender_id=sender_id,
        body="hi",
        created_at=datetime.now(timezone.utc),
    )

    async def fake_send(db, conversation_id, sender_sid, body):
        assert conversation_id == conv_id
        assert sender_sid == sender_id
        return sent

    mock_redis = MagicMock()
    mock_redis.idempotency_try_begin = AsyncMock(return_value="leader")
    mock_redis.idempotency_set_result = AsyncMock()
    mock_redis.idempotency_delete = AsyncMock()

    monkeypatch.setattr(chat_router_module, "send_message", fake_send)
    monkeypatch.setattr(chat_router_module, "redis_client", mock_redis)
    monkeypatch.setattr(chat_router_module.crud_user, "update_last_active", AsyncMock())

    out = await chat_router_module.post_message(
        conversation_id=conv_id,
        data=MessageCreate(body="hi"),
        db=db_session,
        current_user=dummy_user,
        _=None,
        idempotency_key="idem-key-1",
    )

    assert out.message_id == 99
    mock_redis.idempotency_try_begin.assert_awaited_once()
    mock_redis.idempotency_set_result.assert_awaited_once()
    args = mock_redis.idempotency_set_result.await_args[0]
    assert args[1] == sent.model_dump_json()
    mock_redis.idempotency_delete.assert_not_awaited()
    assert mock_redis.idempotency_try_begin.await_args[0][0] == (
        f"idempotency:chat_message:{sender_id}:idem-key-1"
    )


@pytest.mark.asyncio
async def test_post_message_completed_replays_cached_without_send(monkeypatch, db_session):
    conv_id = uuid4()
    sender_id = uuid4()

    dummy_user = MagicMock(spec=User)
    dummy_user.user_id = sender_id

    sent = MessageResponse(
        message_id=99,
        conversation_id=conv_id,
        sender_id=sender_id,
        body="hi",
        created_at=datetime.now(timezone.utc),
    )
    cached = sent.model_dump_json()

    calls = []

    async def bad_send(*args, **kwargs):
        calls.append(True)
        raise AssertionError("send_message must not run on completed replay")

    mock_try = AsyncMock(return_value=f"completed:{cached}")

    mock_redis = MagicMock()
    mock_redis.idempotency_try_begin = mock_try
    mock_redis.idempotency_set_result = AsyncMock()
    mock_redis.idempotency_delete = AsyncMock()

    monkeypatch.setattr(chat_router_module, "send_message", bad_send)
    monkeypatch.setattr(chat_router_module, "redis_client", mock_redis)

    out = await chat_router_module.post_message(
        conversation_id=conv_id,
        data=MessageCreate(body="hi"),
        db=db_session,
        current_user=dummy_user,
        _=None,
        idempotency_key="idem-key-2",
    )

    assert out == sent
    assert calls == []


@pytest.mark.asyncio
async def test_post_message_mismatch_raises_422(monkeypatch, db_session):
    conv_id = uuid4()
    sender_id = uuid4()

    dummy_user = MagicMock(spec=User)
    dummy_user.user_id = sender_id

    mock_redis = MagicMock()
    mock_redis.idempotency_try_begin = AsyncMock(return_value="mismatch")

    monkeypatch.setattr(chat_router_module, "redis_client", mock_redis)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        await chat_router_module.post_message(
            conversation_id=conv_id,
            data=MessageCreate(body="hi"),
            db=db_session,
            current_user=dummy_user,
            _=None,
            idempotency_key="idem-key-mismatch",
        )
    assert ei.value.status_code == 422
