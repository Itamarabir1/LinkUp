from app.core.exceptions.billing import PaymentTransitionError
from app.domain.billing.model import Payment, PaymentStatus

ALLOWED_TRANSITIONS: dict[PaymentStatus, list[PaymentStatus]] = {
    PaymentStatus.PENDING: [PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.CANCELED],
    PaymentStatus.SUCCEEDED: [],
    PaymentStatus.FAILED: [],
    PaymentStatus.CANCELED: [],
}


def validate_transition(payment: Payment, new_status: PaymentStatus) -> None:
    current = payment.status
    allowed = ALLOWED_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise PaymentTransitionError(from_status=current, to_status=new_status)
