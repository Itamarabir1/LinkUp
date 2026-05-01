from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions.billing import (
    CheckoutSessionError,
    IdempotencyMismatchError,
    PaymentAlreadyExistsError,
    PaymentNotFoundError,
    PaymentTransitionError,
    StripeWebhookError,
    UserAlreadyPremiumError,
)
from app.domain.billing.service import BillingService


def test_payment_not_found_error_with_payment_id():
    err = PaymentNotFoundError("pay_123")
    assert err.error_code == "PAYMENT_NOT_FOUND"
    assert err.status_code == 404
    assert "pay_123" in err.message


def test_payment_already_exists_error_contract():
    err = PaymentAlreadyExistsError()
    assert err.error_code == "PAYMENT_ALREADY_EXISTS"
    assert err.status_code == 409


def test_checkout_session_error_contract():
    err = CheckoutSessionError()
    assert err.error_code == "CHECKOUT_SESSION_ERROR"
    assert err.status_code == 502


def test_user_already_premium_error_contract():
    err = UserAlreadyPremiumError()
    assert err.error_code == "USER_ALREADY_PREMIUM"
    assert err.status_code == 400


@pytest.mark.asyncio
async def test_create_checkout_session_rejects_premium_user():
    user = SimpleNamespace(is_premium=True)
    db = AsyncMock()
    svc = BillingService()
    with pytest.raises(UserAlreadyPremiumError):
        await svc.create_checkout_session(db, user=user)


@pytest.mark.asyncio
async def test_handle_webhook_missing_signature_raises_domain_error():
    db = AsyncMock()
    svc = BillingService()
    svc.stripe_gateway.construct_webhook_event = AsyncMock(side_effect=StripeWebhookError())
    with pytest.raises(StripeWebhookError):
        await svc.handle_webhook(db, payload=b"{}", stripe_signature="")


@pytest.mark.asyncio
async def test_handle_webhook_invalid_signature_maps_to_domain_error():
    db = AsyncMock()
    svc = BillingService()
    svc.stripe_gateway.construct_webhook_event = AsyncMock(side_effect=StripeWebhookError())
    with pytest.raises(StripeWebhookError):
        await svc.handle_webhook(
            db,
            payload=b"{}",
            stripe_signature="t=1,v1=bad",
        )


@pytest.mark.asyncio
async def test_checkout_completed_duplicate_event_is_still_audited_before_idempotency_return():
    db = AsyncMock()
    event = SimpleNamespace(
        id="evt_dup_123",
        type="checkout.session.completed",
        data_object={
            "id": "cs_test_123",
            "payment_intent": "pi_test_123",
            "metadata": {"user_id": "11111111-1111-1111-1111-111111111111"},
            "amount_total": 2990,
            "currency": "ils",
        },
    )
    svc = BillingService()
    svc.stripe_gateway.construct_webhook_event = AsyncMock(return_value=event)
    svc.handle_checkout_completed = AsyncMock()
    res = await svc.handle_webhook(
        db,
        payload=b"{}",
        stripe_signature="sig_ok",
    )
    assert res == {"status": "ok"}
    svc.handle_checkout_completed.assert_awaited_once()


def test_new_exceptions_contracts():
    mismatch = IdempotencyMismatchError()
    assert mismatch.status_code == 422
    assert mismatch.error_code == "IDEMPOTENCY_MISMATCH"
    transition = PaymentTransitionError("pending", "pending")
    assert transition.status_code == 409
    assert transition.error_code == "ILLEGAL_PAYMENT_TRANSITION"
