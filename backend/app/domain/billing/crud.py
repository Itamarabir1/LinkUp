import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.model import Payment, PaymentStatus

logger = logging.getLogger(__name__)


class CRUDBilling:
    """
    Async CRUD for Payment - DDD-style service boundary.
    """

    async def get_by_payment_intent_id(self, db: AsyncSession, stripe_payment_intent_id: str) -> Payment | None:
        result = await db.execute(
            select(Payment).where(
                Payment.stripe_payment_intent_id == stripe_payment_intent_id,
            ),
        )
        return result.scalars().first()

    async def get_by_session_id(self, db: AsyncSession, stripe_session_id: str) -> Payment | None:
        result = await db.execute(select(Payment).where(Payment.stripe_session_id == stripe_session_id))
        return result.scalars().first()

    async def get_by_event_id(self, db: AsyncSession, stripe_event_id: str) -> Payment | None:
        result = await db.execute(select(Payment).where(Payment.stripe_event_id == stripe_event_id))
        return result.scalars().first()

    async def create_payment(
        self,
        db: AsyncSession,
        user_id: UUID,
        amount: Decimal,
        currency: str = "ils",
        stripe_session_id: str | None = None,
        stripe_event_id: str | None = None,
        status: PaymentStatus = PaymentStatus.PENDING,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            amount=amount,
            currency=currency.lower(),
            stripe_session_id=stripe_session_id,
            stripe_event_id=stripe_event_id,
            status=status,
        )
        db.add(payment)
        await db.flush()
        await db.refresh(payment)
        return payment

    async def update_payment_status(
        self,
        db: AsyncSession,
        payment: Payment,
        status: PaymentStatus,
        stripe_payment_intent_id: str | None = None,
        stripe_event_id: str | None = None,
    ) -> Payment:
        payment.status = status
        if stripe_payment_intent_id:
            payment.stripe_payment_intent_id = stripe_payment_intent_id
        if stripe_event_id:
            payment.stripe_event_id = stripe_event_id
        db.add(payment)
        await db.flush()
        await db.refresh(payment)
        return payment

    async def get_user_payments(self, db: AsyncSession, user_id: UUID) -> list[Payment]:
        result = await db.execute(
            select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()),
        )
        return list(result.scalars().all())


crud_billing = CRUDBilling()
