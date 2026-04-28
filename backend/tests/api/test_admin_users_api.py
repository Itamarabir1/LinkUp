from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.audit.model import AuditLog
from tests.helpers.db_factories import make_user


@pytest_asyncio.fixture
async def seeded_admin_users(e2e_session_factory: async_sessionmaker):
    async with e2e_session_factory() as s:
        actor_admin = await make_user(s, "admin-actor", email_suffix="adminapi")
        actor_admin.is_admin = True
        target_user = await make_user(s, "admin-target", email_suffix="adminapi")
        await s.commit()
        return {"actor_admin": actor_admin, "target_user": target_user}


@pytest.mark.asyncio
async def test_admin_grant_writes_rich_audit(seeded_admin_users, api_client_with_overrides, e2e_session_factory):
    client, auth_ctx = api_client_with_overrides
    actor = seeded_admin_users["actor_admin"]
    target = seeded_admin_users["target_user"]
    auth_ctx["user"] = actor

    response = await client.patch(
        f"/api/v1/admin/users/{target.user_id}/admin",
        params={"action": "grant", "reason": "incident-escalation"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action"] == "grant"
    assert body["before_is_admin"] is False
    assert body["after_is_admin"] is True
    assert body["changed"] is True

    async with e2e_session_factory() as s:
        row = (
            await s.execute(
                select(AuditLog)
                .where(AuditLog.resource_id == str(target.user_id))
                .order_by(AuditLog.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
        assert row is not None
        assert row.action == "grant_user_admin"
        assert row.metadata_json["target_email"] == target.email
        assert row.metadata_json["before_is_admin"] is False
        assert row.metadata_json["after_is_admin"] is True
        assert row.metadata_json["requested_action"] == "grant"
        assert row.metadata_json["reason"] == "incident-escalation"


@pytest.mark.asyncio
async def test_admin_self_demotion_blocked(seeded_admin_users, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    actor = seeded_admin_users["actor_admin"]
    auth_ctx["user"] = actor

    response = await client.patch(
        f"/api/v1/admin/users/{actor.user_id}/admin",
        params={"action": "revoke"},
    )
    assert response.status_code == 400, response.text
    assert "Self-demotion" in response.text
