import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.domain.billing.crud import crud_billing
from app.domain.billing.idempotency import IdempotencyManager
from app.domain.billing.model import Payment
from app.domain.billing.service import BillingService
from app.domain.billing.stripe_gateway import StripeGateway, StripeSessionDTO
from app.db.session import SessionLocal
from app.infrastructure.metrics import (
    billing_reconciler_errors_total,
    billing_reconciler_recovered_total,
    billing_reconciler_runs_total,
)

logger = logging.getLogger(__name__)

RECONCILER_ADVISORY_LOCK_KEY = 440_117_901


class BillingReconciler:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] = SessionLocal,
        billing_service: BillingService | None = None,
        stripe_gateway: StripeGateway | None = None,
        idempotency_manager: IdempotencyManager | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.billing_service = billing_service or BillingService()
        self.stripe_gateway = stripe_gateway or StripeGateway()
        self.idempotency_manager = idempotency_manager or IdempotencyManager()
        self.last_run_at: datetime | None = None

    async def run(self) -> None:
        if not settings.BILLING_RECONCILER_ENABLED:
            logger.info("billing reconciler disabled by config")
            return
        async with self.session_factory() as db:
            got_lock = await self._try_advisory_lock(db)
            if not got_lock:
                logger.info("reconciler skipped: another instance running")
                return
            try:
                billing_reconciler_runs_total.inc()
                self.last_run_at = datetime.now(UTC)
                await self.idempotency_manager.cleanup_expired(db)
                await db.commit()
                stale = await self._fetch_stale_pending(db)
                for payment in stale:
                    async with self.session_factory() as db_pay:
                        try:
                            recovered = await self._reconcile_one(db_pay, payment)
                            if recovered:
                                billing_reconciler_recovered_total.inc()
                            await db_pay.commit()
                        except Exception as exc:  # noqa: BLE001
                            await db_pay.rollback()
                            billing_reconciler_errors_total.inc()
                            logger.exception(
                                "billing reconciler failed payment_id=%s session=%s: %s",
                                payment.payment_id,
                                payment.stripe_session_id,
                                exc,
                            )
            finally:
                await self._release_advisory_lock(db)

    async def reconcile_one_by_payment_id(self, payment_id: UUID) -> tuple[str, str, str]:
        async with self.session_factory() as db:
            payment = await crud_billing.get_payment_by_id(db, payment_id=payment_id)
            if not payment:
                raise ValueError(f"payment not found: {payment_id}")
            old_status = payment.status.value
            action = "skipped"
            recovered = await self._reconcile_one(db, payment)
            if recovered:
                action = "recovered"
                billing_reconciler_recovered_total.inc()
            await db.commit()
            new_status = payment.status.value
            return old_status, new_status, action

    async def _fetch_stale_pending(self, db: AsyncSession) -> list[Payment]:
        min_age = datetime.now(UTC) - timedelta(minutes=settings.BILLING_PENDING_MIN_AGE_MINUTES)
        max_age = datetime.now(UTC) - timedelta(hours=settings.BILLING_PENDING_MAX_AGE_HOURS)
        return await crud_billing.list_stale_pending_payments(db, min_age=min_age, max_age=max_age, limit=500)

    async def _reconcile_one(self, db: AsyncSession, payment: Payment) -> bool:
        if not payment.stripe_session_id:
            return False
        session = await self.stripe_gateway.retrieve_session(payment.stripe_session_id)
        return await self._apply_session_result(db, payment, session)

    async def _apply_session_result(self, db: AsyncSession, payment: Payment, session: StripeSessionDTO) -> bool:
        if session.payment_status == "paid":
            amount = Decimal(session.amount_total or 0) / Decimal("100")
            await self.billing_service.handle_checkout_completed(
                db,
                stripe_session_id=session.id,
                stripe_payment_intent_id=session.payment_intent,
                stripe_event_id=None,
                user_id=session.metadata.get("user_id"),
                amount=amount,
                currency=(session.currency or "ils").lower(),
            )
            return True
        if session.status == "expired":
            await self.billing_service.handle_session_expired(
                db,
                stripe_session_id=session.id,
                stripe_event_id=None,
            )
            return True
        if session.payment_status == "unpaid":
            return False
        return False

    async def _try_advisory_lock(self, db: AsyncSession) -> bool:
        result = await db.execute(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": RECONCILER_ADVISORY_LOCK_KEY},
        )
        return bool(result.scalar())

    async def _release_advisory_lock(self, db: AsyncSession) -> None:
        await db.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": RECONCILER_ADVISORY_LOCK_KEY},
        )


billing_reconciler = BillingReconciler()
