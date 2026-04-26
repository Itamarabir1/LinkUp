from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.domain.chat import crud as chat_crud
from app.domain.chat.model import Conversation, ConversationParticipant
from tests.helpers.db_factories import make_user


async def _make_conversation_with_participants(db_session):
    user_a = await make_user(db_session, "chat-a", email_suffix="chat")
    user_b = await make_user(db_session, "chat-b", email_suffix="chat")
    user_1_id, user_2_id = (user_a.user_id, user_b.user_id) if user_a.user_id < user_b.user_id else (user_b.user_id, user_a.user_id)
    conv = Conversation(conversation_id=uuid4(), user_id_1=user_1_id, user_id_2=user_2_id)
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
async def test_mark_conversation_read_advances_last_read_message_id(db_session):
    conv, current_user, partner = await _make_conversation_with_participants(db_session)
    m1 = await chat_crud.create_message(db_session, conv.conversation_id, partner.user_id, "one")
    await chat_crud.create_message(db_session, conv.conversation_id, partner.user_id, "two")
    m3 = await chat_crud.create_message(db_session, conv.conversation_id, partner.user_id, "three")

    await chat_crud.mark_conversation_read(db_session, conv.conversation_id, current_user.user_id)

    participant = await db_session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == current_user.user_id,
        )
    )
    assert participant is not None
    assert participant.last_read_message_id == m3.message_id
    assert participant.last_read_message_id > m1.message_id


@pytest.mark.asyncio
async def test_mark_conversation_read_is_monotonic(db_session):
    conv, current_user, partner = await _make_conversation_with_participants(db_session)

    participant = await db_session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == current_user.user_id,
        )
    )
    assert participant is not None
    participant.last_read_message_id = 10
    await db_session.flush()

    await chat_crud.mark_conversation_read(db_session, conv.conversation_id, current_user.user_id)

    refreshed = await db_session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == current_user.user_id,
        )
    )
    assert refreshed is not None
    assert refreshed.last_read_message_id == 10


@pytest.mark.asyncio
async def test_get_partner_read_up_to_message_id_returns_correct_cursor(db_session):
    conv, current_user, partner = await _make_conversation_with_participants(db_session)

    partner_participant = await db_session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == partner.user_id,
        )
    )
    assert partner_participant is not None
    partner_participant.last_read_message_id = 5
    await db_session.flush()

    read_up_to = await chat_crud.get_partner_read_up_to_message_id(db_session, conv.conversation_id, current_user.user_id)
    assert read_up_to == 5


@pytest.mark.asyncio
async def test_mark_conversation_read_keeps_cursor_none_for_empty_conversation(db_session):
    conv, current_user, _partner = await _make_conversation_with_participants(db_session)

    await chat_crud.mark_conversation_read(db_session, conv.conversation_id, current_user.user_id)

    participant = await db_session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == current_user.user_id,
        )
    )
    assert participant is not None
    assert participant.last_read_message_id is None


@pytest.mark.asyncio
async def test_get_partner_read_up_to_message_id_returns_partner_cursor_without_outgoing_messages(db_session):
    conv, current_user, partner = await _make_conversation_with_participants(db_session)
    await chat_crud.create_message(db_session, conv.conversation_id, partner.user_id, "only inbound")

    partner_participant = await db_session.scalar(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conv.conversation_id,
            ConversationParticipant.user_id == partner.user_id,
        )
    )
    assert partner_participant is not None
    partner_participant.last_read_message_id = 5
    await db_session.flush()

    read_up_to = await chat_crud.get_partner_read_up_to_message_id(db_session, conv.conversation_id, current_user.user_id)
    assert read_up_to == 5
