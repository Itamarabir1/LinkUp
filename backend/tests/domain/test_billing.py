from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions.billing import (
    CheckoutSessionError,
    PaymentAlreadyExistsError,
    PaymentNotFoundError,
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
    with pytest.raises(UserAlreadyPremiumError):
        await BillingService.create_checkout_session(db, user=user)


@pytest.mark.asyncio
async def test_handle_webhook_missing_signature_raises_domain_error():
    db = AsyncMock()
    with pytest.raises(StripeWebhookError):
        await BillingService.handle_webhook(db, payload=b"{}", stripe_signature="")


@pytest.mark.asyncio
async def test_handle_webhook_invalid_signature_maps_to_domain_error():
    db = AsyncMock()
    with patch(
        "app.domain.billing.service.stripe.Webhook.construct_event",
        side_effect=ValueError("bad signature"),
    ):
        with pytest.raises(StripeWebhookError):
            await BillingService.handle_webhook(
                db,
                payload=b"{}",
                stripe_signature="t=1,v1=bad",
            )
