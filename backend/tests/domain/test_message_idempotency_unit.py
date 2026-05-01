"""Unit tests for chat message Idempotency-Key helpers."""

from uuid import uuid4

from app.domain.chat.message_idempotency import (
    chat_message_redis_key,
    message_send_fingerprint,
)


def test_chat_message_redis_key_includes_user_and_client():
    uid = uuid4()
    key = chat_message_redis_key(str(uid), "client-abcd")
    assert key == f"idempotency:chat_message:{uid}:client-abcd"


def test_message_send_fingerprint_stable():
    cid = uuid4()
    fp1 = message_send_fingerprint(cid, "hello")
    fp2 = message_send_fingerprint(cid, "hello")
    assert fp1 == fp2
    assert len(fp1) == 64


def test_message_send_fingerprint_differs_body():
    cid = uuid4()
    assert message_send_fingerprint(cid, "a") != message_send_fingerprint(cid, "b")


def test_message_send_fingerprint_differs_conversation():
    assert message_send_fingerprint(uuid4(), "x") != message_send_fingerprint(uuid4(), "x")
