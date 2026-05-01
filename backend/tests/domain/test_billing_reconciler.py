from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.billing.reconciler import BillingReconciler
from app.domain.billing.stripe_gateway import StripeSessionDTO


class _DummySessionCtx:
    def __init__(self, db):
        self.db = db

    async def __aenter__(self):
        return self.db

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_reconcile_paid_session_triggers_checkout_completed():
    payment = SimpleNamespace(payment_id="p1", stripe_session_id="cs_1")
    svc = AsyncMock()
    gateway = AsyncMock()
    gateway.retrieve_session = AsyncMock(
        return_value=StripeSessionDTO(
            id="cs_1",
            url=None,
            status="complete",
            payment_status="paid",
            payment_intent="pi_1",
            currency="ils",
            amount_total=2990,
            metadata={"user_id": "11111111-1111-1111-1111-111111111111"},
        ),
    )
    rec = BillingReconciler(
        session_factory=lambda: _DummySessionCtx(AsyncMock()),
        billing_service=svc,
        stripe_gateway=gateway,
    )
    ok = await rec._reconcile_one(AsyncMock(), payment)
    assert ok is True
    svc.handle_checkout_completed.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_expired_session_cancels_payment():
    payment = SimpleNamespace(payment_id="p1", stripe_session_id="cs_2")
    svc = AsyncMock()
    gateway = AsyncMock()
    gateway.retrieve_session = AsyncMock(
        return_value=StripeSessionDTO(
            id="cs_2",
            url=None,
            status="expired",
            payment_status="unpaid",
            payment_intent=None,
            currency="ils",
            amount_total=2990,
            metadata={},
        ),
    )
    rec = BillingReconciler(
        session_factory=lambda: _DummySessionCtx(AsyncMock()),
        billing_service=svc,
        stripe_gateway=gateway,
    )
    ok = await rec._reconcile_one(AsyncMock(), payment)
    assert ok is True
    svc.handle_session_expired.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconciler_loop_continues_after_single_payment_error():
    db = AsyncMock()
    rec = BillingReconciler(session_factory=lambda: _DummySessionCtx(db))
    rec._try_advisory_lock = AsyncMock(return_value=True)
    rec._release_advisory_lock = AsyncMock()
    rec.idempotency_manager.cleanup_expired = AsyncMock(return_value=0)
    rec._fetch_stale_pending = AsyncMock(
        return_value=[SimpleNamespace(payment_id="a", stripe_session_id="a"), SimpleNamespace(payment_id="b", stripe_session_id="b")],
    )
    rec._reconcile_one = AsyncMock(side_effect=[RuntimeError("boom"), False])
    await rec.run()
    assert rec._reconcile_one.await_count == 2
