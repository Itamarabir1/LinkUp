from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.exceptions.billing import IdempotencyMismatchError
from app.domain.billing.idempotency import IdempotencyManager


@pytest.mark.asyncio
async def test_idempotency_same_key_same_fingerprint_returns_cached(db_session):
    manager = IdempotencyManager()
    user_id = uuid4()
    endpoint = "/billing/checkout"
    key = "k-123"
    fingerprint = "fp-1"
    body = {"checkout_url": "https://example", "session_id": "cs_1"}

    await manager.store(
        db_session,
        user_id=user_id,
        client_key=key,
        endpoint=endpoint,
        request_fingerprint=fingerprint,
        response_body=body,
        status_code=201,
        ttl_hours=1,
    )
    hit = await manager.check(
        db_session,
        user_id=user_id,
        client_key=key,
        endpoint=endpoint,
        request_fingerprint=fingerprint,
    )
    assert hit is not None
    assert hit.response_body == body
    assert hit.status_code == 201


@pytest.mark.asyncio
async def test_idempotency_same_key_different_fingerprint_raises(db_session):
    manager = IdempotencyManager()
    user_id = uuid4()
    endpoint = "/billing/checkout"
    key = "k-123"
    await manager.store(
        db_session,
        user_id=user_id,
        client_key=key,
        endpoint=endpoint,
        request_fingerprint="fp-1",
        response_body={"ok": True},
        status_code=201,
        ttl_hours=1,
    )
    with pytest.raises(IdempotencyMismatchError):
        await manager.check(
            db_session,
            user_id=user_id,
            client_key=key,
            endpoint=endpoint,
            request_fingerprint="fp-2",
        )


@pytest.mark.asyncio
async def test_idempotency_expired_key_is_not_cache_hit(db_session):
    manager = IdempotencyManager()
    user_id = uuid4()
    endpoint = "/billing/checkout"
    key = "k-123"
    await manager.store(
        db_session,
        user_id=user_id,
        client_key=key,
        endpoint=endpoint,
        request_fingerprint="fp-1",
        response_body={"ok": True},
        status_code=201,
        ttl_hours=1,
    )
    await db_session.execute(
        text("UPDATE idempotency_keys SET expires_at=:exp WHERE user_id=:uid"),
        {"exp": datetime.now(UTC) - timedelta(minutes=1), "uid": user_id},
    )
    hit = await manager.check(
        db_session,
        user_id=user_id,
        client_key=key,
        endpoint=endpoint,
        request_fingerprint="fp-1",
    )
    assert hit is None
