"""Tests for publish_read_receipt Redis payload contract (chat-ws routing)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.domain.chat import crud as chat_crud
from app.domain.chat import service as chat_service
from app.domain.chat.model import Conversation, ConversationParticipant
from tests.helpers.db_factories import make_user


async def _conversation_with_pair(db_session):
    user_a = await make_user(db_session, "rr-a", email_suffix="rr")
    user_b = await make_user(db_session, "rr-b", email_suffix="rr")
    u1, u2 = (
        (user_a.user_id, user_b.user_id)
        if user_a.user_id < user_b.user_id
        else (user_b.user_id, user_a.user_id)
    )
    conv = Conversation(conversation_id=uuid4(), user_id_1=u1, user_id_2=u2)
    db_session.add(conv)
    db_session.add_all(
        [
            ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_a.user_id),
            ConversationParticipant(conversation_id=conv.conversation_id, user_id=user_b.user_id),
        ]
    )
    await db_session.flush()
    return conv, user_a, user_b


@pytest.mark.asyncio
async def test_publish_read_receipt_includes_recipient_id_partner(db_session):
    """message_read must include recipient_id for chat-ws PublishChatMessage routing."""
    conv, reader, partner = await _conversation_with_pair(db_session)
    await chat_crud.create_message(db_session, conv.conversation_id, partner.user_id, "hi")
    await chat_crud.mark_conversation_read(db_session, conv.conversation_id, reader.user_id)
    await db_session.flush()

    mock_publish = AsyncMock(return_value=None)
    with patch("app.domain.chat.service.redis_chat_pubsub.publish", mock_publish):
        await chat_service.publish_read_receipt(db_session, conv.conversation_id, reader.user_id)

    mock_publish.assert_awaited_once()
    channel, raw = mock_publish.await_args[0]
    assert channel == f"chat:conversation:{conv.conversation_id}"
    body = json.loads(raw)
    assert body["type"] == "message_read"
    assert body["reader_id"] == str(reader.user_id)
    assert body["recipient_id"] == str(partner.user_id)
    assert body["recipient_id"] != body["reader_id"]
    assert "read_up_to_message_id" in body
