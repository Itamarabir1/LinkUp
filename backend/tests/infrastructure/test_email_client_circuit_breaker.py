"""EmailClient integration with brevo_email_cb — fail-fast when OPEN."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _ensure_sib_sdk_stub() -> None:
    """Real Brevo SDK import can stall in some CI/sandbox environments; stub minimal surface."""
    if "sib_api_v3_sdk" in sys.modules:
        return

    rest = ModuleType("sib_api_v3_sdk.rest")

    class ApiException(Exception):
        def __init__(self, status=None, reason=None, http_resp=None):
            super().__init__(reason or str(status))
            self.status = status
            self.reason = reason

    rest.ApiException = ApiException

    class _Passthrough:
        def __init__(self, *args, **kwargs) -> None:
            pass

    class _Configuration:
        """Minimal shape: EmailClient sets self.configuration.api_key['api-key']."""

        def __init__(self, *args, **kwargs) -> None:
            self.api_key: dict[str, str] = {"api-key": ""}

    class _EmailsApi:
        def __init__(self, *args, **kwargs) -> None:
            self.send_transac_email = MagicMock(return_value={"messageId": "stub"})

    mod = ModuleType("sib_api_v3_sdk")
    mod.rest = rest
    mod.Configuration = _Configuration
    mod.ApiClient = _Passthrough
    mod.TransactionalEmailsApi = _EmailsApi
    mod.SendSmtpEmail = _Passthrough

    sys.modules["sib_api_v3_sdk"] = mod
    sys.modules["sib_api_v3_sdk.rest"] = rest


_ensure_sib_sdk_stub()

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

    from sib_api_v3_sdk.rest import ApiException as RestApiExc

    async def always_fail(
        self: EmailClient,
        recipient: str,
        subject: str,
        body: str,
        recipient_name: str = "User",
    ) -> None:
        raise RestApiExc(status=503, reason="service unavailable")

    monkeypatch.setattr(EmailClient, "_send_with_retry", always_fail)

    with pytest.raises(RestApiExc):
        await client.send("u@example.com", "subject", "<p>hi</p>")

    spy_fail.assert_called_once()
    spy_ok.assert_not_called()
