from types import SimpleNamespace

import pytest

from app.core.exceptions.billing import PaymentTransitionError
from app.domain.billing.model import PaymentStatus
from app.domain.billing.state_machine import validate_transition


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (PaymentStatus.PENDING, PaymentStatus.SUCCEEDED),
        (PaymentStatus.PENDING, PaymentStatus.FAILED),
        (PaymentStatus.PENDING, PaymentStatus.CANCELED),
    ],
)
def test_legal_transitions(from_status: PaymentStatus, to_status: PaymentStatus):
    payment = SimpleNamespace(status=from_status)
    validate_transition(payment, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (PaymentStatus.SUCCEEDED, PaymentStatus.FAILED),
        (PaymentStatus.SUCCEEDED, PaymentStatus.CANCELED),
        (PaymentStatus.FAILED, PaymentStatus.SUCCEEDED),
        (PaymentStatus.CANCELED, PaymentStatus.SUCCEEDED),
    ],
)
def test_illegal_transitions_raise(from_status: PaymentStatus, to_status: PaymentStatus):
    payment = SimpleNamespace(status=from_status)
    with pytest.raises(PaymentTransitionError):
        validate_transition(payment, to_status)
