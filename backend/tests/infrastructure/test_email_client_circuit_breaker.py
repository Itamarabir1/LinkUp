"""EmailClient integration with brevo_email_cb — fail-fast when OPEN."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sib_api_v3_sdk.rest import ApiException

from app.core.config import settings
from app.core.exceptions.infrastructure import EmailProviderCircuitOpenError
from app.domain.notifications.channels.email import client as email_client_module
from app.domain.notifications.channels.email.client import EmailClient


@pytest.mark.asyncio
async def test_send_fail_fast_raises_when_allow_request_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BREVO_API_KEY", "unit-test-key", raising=False)

    mock_cb = MagicMock()
    mock_cb.allow_request.return_value = False
    monkeypatch.setattr(email_client_module, "brevo_email_cb", mock_cb)

    client = EmailClient()

    with pytest.raises(EmailProviderCircuitOpenError):
        await client.send("u@example.com", "subject", "<p>hi</p>")

    mock_cb.allow_request.assert_called_once()
    mock_cb.record_failure.assert_not_called()
    mock_cb.record_success.assert_not_called()


@pytest.mark.asyncio
async def test_send_records_failure_once_after_retries_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "BREVO_API_KEY", "unit-test-key", raising=False)

    mock_cb = MagicMock()
    mock_cb.allow_request.return_value = True

    spy_fail = MagicMock(wraps=mock_cb.record_failure)
    spy_ok = MagicMock(wraps=mock_cb.record_success)
    mock_cb.record_failure = spy_fail
    mock_cb.record_success = spy_ok
    monkeypatch.setattr(email_client_module, "brevo_email_cb", mock_cb)

    client = EmailClient()

    async def always_fail(
        self: EmailClient,
        recipient: str,
        subject: str,
        body: str,
        recipient_name: str = "User",
    ) -> None:
        raise ApiException(status=503, reason="service unavailable")

    monkeypatch.setattr(EmailClient, "_send_with_retry", always_fail)

    with pytest.raises(ApiException):
        await client.send("u@example.com", "subject", "<p>hi</p>")

    spy_fail.assert_called_once()
    spy_ok.assert_not_called()
