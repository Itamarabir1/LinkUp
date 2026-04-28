from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.billing.model import Payment, PaymentStatus
from app.infrastructure.audit.model import AuditLog
from tests.helpers.db_factories import make_booking, make_ride, make_user


@pytest_asyncio.fixture
async def seeded_admin_surface(e2e_session_factory: async_sessionmaker):
    async with e2e_session_factory() as s:
        admin = await make_user(s, "admin-surface", email_suffix="adminapi")
        admin.is_admin = True
        driver = await make_user(s, "driver-surface", email_suffix="adminapi")
        passenger = await make_user(s, "passenger-surface", email_suffix="adminapi")
        ride = await make_ride(s, driver.user_id)
        booking = await make_booking(s, ride.ride_id, passenger.user_id)
        payment = Payment(
            user_id=passenger.user_id,
            amount=Decimal("49.90"),
            currency="ils",
            status=PaymentStatus.SUCCEEDED,
            stripe_session_id="cs_test_surface_1",
        )
        s.add(payment)
        await s.commit()
        return {"admin": admin, "booking": booking, "payment": payment}


@pytest.mark.asyncio
async def test_admin_bookings_returns_paginated_items(seeded_admin_surface, api_client_with_overrides):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_admin_surface["admin"]

    response = await client.get("/api/v1/admin/bookings", params={"limit": 20, "offset": 0})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert any(row["booking_id"] == str(seeded_admin_surface["booking"].booking_id) for row in body["items"])


@pytest.mark.asyncio
async def test_admin_audit_log_read_writes_audit(seeded_admin_surface, api_client_with_overrides, e2e_session_factory):
    client, auth_ctx = api_client_with_overrides
    auth_ctx["user"] = seeded_admin_surface["admin"]

    response = await client.get("/api/v1/admin/audit-log", params={"limit": 10, "offset": 0})
    assert response.status_code == 200, response.text
    body = response.json()
    assert "items" in body
    assert "next_offset" in body

    async with e2e_session_factory() as s:
        row = (
            await s.execute(
                select(AuditLog).where(AuditLog.action == "admin_audit_log_read").limit(1),
            )
        ).scalars().first()
        assert row is not None
