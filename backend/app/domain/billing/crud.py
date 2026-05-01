import logging
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.model import IdempotencyKey, Payment, PaymentStatus

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

    async def get_payment_by_id(self, db: AsyncSession, *, payment_id: UUID) -> Payment | None:
        result = await db.execute(select(Payment).where(Payment.payment_id == payment_id))
        return result.scalars().first()

    async def list_stale_pending_payments(
        self,
        db: AsyncSession,
        *,
        min_age: datetime,
        max_age: datetime,
        limit: int,
    ) -> list[Payment]:
        result = await db.execute(
            select(Payment)
            .where(
                and_(
                    Payment.status == PaymentStatus.PENDING,
                    Payment.created_at <= min_age,
                    Payment.created_at >= max_age,
                ),
            )
            .order_by(Payment.created_at.asc())
            .limit(limit),
        )
        return list(result.scalars().all())

    async def get_idempotency_key(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        client_key: str,
        endpoint: str,
    ) -> IdempotencyKey | None:
        result = await db.execute(
            select(IdempotencyKey).where(
                and_(
                    IdempotencyKey.user_id == user_id,
                    IdempotencyKey.client_key == client_key,
                    IdempotencyKey.endpoint == endpoint,
                ),
            ),
        )
        return result.scalars().first()

    async def upsert_idempotency_key(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        client_key: str,
        endpoint: str,
        request_fingerprint: str,
        response_body: dict,
        status_code: int,
        expires_at: datetime,
    ) -> IdempotencyKey:
        existing = await self.get_idempotency_key(
            db,
            user_id=user_id,
            client_key=client_key,
            endpoint=endpoint,
        )
        if existing:
            existing.request_fingerprint = request_fingerprint
            existing.response_body = response_body
            existing.status_code = status_code
            existing.expires_at = expires_at
            db.add(existing)
            await db.flush()
            await db.refresh(existing)
            return existing
        record = IdempotencyKey(
            user_id=user_id,
            client_key=client_key,
            endpoint=endpoint,
            request_fingerprint=request_fingerprint,
            response_body=response_body,
            status_code=status_code,
            expires_at=expires_at,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        return record

    async def delete_expired_idempotency_keys(self, db: AsyncSession, *, older_than: datetime) -> int:
        result = await db.execute(delete(IdempotencyKey).where(IdempotencyKey.expires_at <= older_than))
        return int(result.rowcount or 0)


crud_billing = CRUDBilling()
