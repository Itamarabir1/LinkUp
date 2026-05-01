import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions.billing import (
    CheckoutSessionError,
    IdempotencyMismatchError,
    PaymentAlreadyExistsError,
    StripeWebhookError,
    UserAlreadyPremiumError,
)
from app.domain.billing.crud import crud_billing
from app.domain.billing.idempotency import IdempotencyManager, IdempotencyCachedResponse
from app.domain.billing.model import Payment, PaymentStatus
from app.domain.billing.schema import CheckoutResponse, PaymentStatusResponse
from app.domain.billing.state_machine import validate_transition
from app.domain.billing.stripe_gateway import StripeGateway
from app.domain.users.crud import crud_user
from app.domain.users.model import User
from app.infrastructure.audit.repo import audit_repo
from app.infrastructure.metrics import (
    billing_idempotency_hits_total,
    payments_initiated_total,
    payments_failed_total,
    payments_succeeded_total,
    payments_canceled_total,
    stripe_webhook_errors_total,
    stripe_webhook_received_total,
)

logger = logging.getLogger(__name__)

# Premium plan price - set in Stripe Dashboard, store ID in env
PREMIUM_PRICE_ILS = Decimal("29.90")


class BillingService:
    def __init__(
        self,
        *,
        stripe_gateway: StripeGateway | None = None,
        idempotency_manager: IdempotencyManager | None = None,
    ) -> None:
        self.stripe_gateway = stripe_gateway or StripeGateway()
        self.idempotency_manager = idempotency_manager or IdempotencyManager()

    async def create_checkout_session(
        self,
        db: AsyncSession,
        user: User,
        *,
        idempotency_key: str | None = None,
        request_fingerprint: str | None = None,
        endpoint: str = "/billing/checkout",
    ) -> tuple[CheckoutResponse, int]:
        """
        Create a Stripe Checkout Session for premium upgrade.
        Creates or reuses stripe_customer_id on the user.
        """
        if user.is_premium:
            raise UserAlreadyPremiumError()
        if idempotency_key and not request_fingerprint:
            raise IdempotencyMismatchError()
        cached: IdempotencyCachedResponse | None = None
        if idempotency_key and request_fingerprint:
            cached = await self.idempotency_manager.check(
                db,
                user_id=user.user_id,
                client_key=idempotency_key,
                endpoint=endpoint,
                request_fingerprint=request_fingerprint,
            )
            if cached:
                billing_idempotency_hits_total.inc()
                return CheckoutResponse(**cached.response_body), cached.status_code

        try:
            # 1. Get or create Stripe customer
            if not getattr(user, "stripe_customer_id", None):
                customer = await self.stripe_gateway.create_customer(
                    email=user.email,
                    name=user.full_name,
                    user_id=str(user.user_id),
                )
                await crud_user.update_stripe_customer_id(
                    db,
                    user=user,
                    stripe_customer_id=customer.id,
                )
                stripe_customer_id = customer.id
            else:
                stripe_customer_id = user.stripe_customer_id

            # 2. Create Checkout Session
            session = await self.stripe_gateway.create_checkout_session(
                customer_id=stripe_customer_id,
                amount=PREMIUM_PRICE_ILS,
                metadata={"user_id": str(user.user_id)},
            )

            # 3. Save pending payment record
            await crud_billing.create_payment(
                db,
                user_id=user.user_id,
                amount=PREMIUM_PRICE_ILS,
                currency="ils",
                stripe_session_id=session.id,
                status=PaymentStatus.PENDING,
            )
            await db.commit()
            payments_initiated_total.inc()
            payload = CheckoutResponse(checkout_url=session.url or "", session_id=session.id)
            if idempotency_key and request_fingerprint:
                await self.idempotency_manager.store(
                    db,
                    user_id=user.user_id,
                    client_key=idempotency_key,
                    endpoint=endpoint,
                    request_fingerprint=request_fingerprint,
                    response_body=payload.model_dump(),
                    status_code=201,
                    ttl_hours=settings.BILLING_IDEMPOTENCY_TTL_HOURS,
                )
                await db.commit()

            logger.info(
                "Checkout session created for user=%s session=%s",
                user.user_id,
                session.id,
            )
            return payload, 201

        except IntegrityError as e:
            await db.rollback()
            logger.warning("Duplicate payment record for checkout session: %s", e)
            raise PaymentAlreadyExistsError() from e
        except CheckoutSessionError:
            await db.rollback()
            raise
        except Exception as e:
            await db.rollback()
            logger.error("Unexpected error creating checkout: %s", e)
            raise CheckoutSessionError() from e

    async def handle_webhook(
        self,
        db: AsyncSession,
        payload: bytes,
        stripe_signature: str,
    ) -> dict:
        """
        Handle Stripe webhook: verify signature; route by event type.
        Supported: checkout.session.completed / checkout.session.expired / payment_intent.payment_failed.
        Idempotent — safe to replay the same event / payment intent paths.
        """
        try:
            event = await self.stripe_gateway.construct_webhook_event(
                payload=payload,
                signature=stripe_signature,
            )
            stripe_webhook_received_total.labels(event_type=event.type).inc()
        except StripeWebhookError:
            stripe_webhook_errors_total.inc()
            raise

        if event.type == "checkout.session.completed":
            await self.handle_checkout_completed(
                db,
                stripe_session_id=event.data_object.get("id"),
                stripe_payment_intent_id=event.data_object.get("payment_intent"),
                stripe_event_id=event.id,
                user_id=event.data_object.get("metadata", {}).get("user_id"),
                amount=Decimal(str(event.data_object.get("amount_total", 0))) / Decimal("100"),
                currency=str(event.data_object.get("currency", "ils")).lower(),
            )
        elif event.type == "checkout.session.expired":
            await self.handle_session_expired(
                db,
                stripe_session_id=event.data_object.get("id"),
                stripe_event_id=event.id,
            )
        elif event.type == "payment_intent.payment_failed":
            await self.handle_payment_failed(
                db,
                stripe_payment_intent_id=event.data_object.get("id"),
                stripe_event_id=event.id,
            )

        return {"status": "ok"}

    async def handle_checkout_completed(
        self,
        db: AsyncSession,
        *,
        stripe_session_id: str | None,
        stripe_payment_intent_id: str | None,
        stripe_event_id: str | None,
        user_id: str | None,
        amount: Decimal,
        currency: str,
    ) -> None:
        if not user_id or not stripe_payment_intent_id:
            logger.warning("checkout completed missing user/payment_intent session=%s", stripe_session_id)
            return

        try:
            await audit_repo.record(
                db,
                actor_user_id=UUID(user_id) if user_id else None,
                action="billing_checkout_completed_webhook",
                resource_type="billing_webhook",
                resource_id=stripe_event_id or stripe_session_id,
                metadata={
                    "event_type": "checkout.session.completed",
                    "stripe_event_id": stripe_event_id,
                    "stripe_session_id": stripe_session_id,
                    "stripe_payment_intent_id": stripe_payment_intent_id,
                },
                ip_address=None,
            )
            await db.commit()
        except Exception as audit_exc:
            await db.rollback()
            logger.warning("Audit log write failed for Stripe webhook attempt: %s", audit_exc)

        if stripe_event_id:
            existing_event = await crud_billing.get_by_event_id(db, stripe_event_id)
            if existing_event:
                logger.info("Webhook event already processed event_id=%s", stripe_event_id)
                return

        existing_payment = await crud_billing.get_by_payment_intent_id(
            db,
            stripe_payment_intent_id,
        )
        if existing_payment and existing_payment.status == PaymentStatus.SUCCEEDED:
            logger.info(
                "Webhook already processed for payment_intent=%s",
                stripe_payment_intent_id,
            )
            return

        payment = await crud_billing.get_by_session_id(db, stripe_session_id)
        if payment:
            await self.transition_payment_status(
                db,
                payment=payment,
                new_status=PaymentStatus.SUCCEEDED,
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_event_id=stripe_event_id,
            )
        else:
            payment = Payment(
                user_id=UUID(user_id),
                amount=amount,
                currency=currency.lower(),
                stripe_session_id=stripe_session_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
                stripe_event_id=stripe_event_id,
                status=PaymentStatus.SUCCEEDED,
            )
            db.add(payment)
            await db.flush()

        user = await crud_user.get_by_id(db, UUID(user_id))
        if user and not user.is_premium:
            await crud_user.mark_as_premium(db, user=user)

        await db.commit()
        payments_succeeded_total.inc()
        logger.info("User %s upgraded to premium", user_id)

    async def handle_session_expired(
        self,
        db: AsyncSession,
        *,
        stripe_session_id: str | None,
        stripe_event_id: str | None,
    ) -> None:
        if not stripe_session_id:
            return
        if stripe_event_id:
            existing_event = await crud_billing.get_by_event_id(db, stripe_event_id)
            if existing_event:
                return
        payment = await crud_billing.get_by_session_id(db, stripe_session_id)
        if not payment:
            return
        await self.transition_payment_status(
            db,
            payment=payment,
            new_status=PaymentStatus.CANCELED,
            stripe_event_id=stripe_event_id,
        )
        await db.commit()
        payments_canceled_total.inc()

    async def handle_payment_failed(
        self,
        db: AsyncSession,
        *,
        stripe_payment_intent_id: str | None,
        stripe_event_id: str | None,
    ) -> None:
        if not stripe_payment_intent_id:
            return
        if stripe_event_id:
            existing_event = await crud_billing.get_by_event_id(db, stripe_event_id)
            if existing_event:
                return
        payment = await crud_billing.get_by_payment_intent_id(db, stripe_payment_intent_id)
        if not payment:
            logger.warning(
                "payment_failed event for unknown intent=%s, skipping",
                stripe_payment_intent_id,
            )
            return
        await self.transition_payment_status(
            db,
            payment=payment,
            new_status=PaymentStatus.FAILED,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_event_id=stripe_event_id,
        )
        await db.commit()
        payments_failed_total.inc()

    async def transition_payment_status(
        self,
        db: AsyncSession,
        *,
        payment: Payment,
        new_status: PaymentStatus,
        stripe_payment_intent_id: str | None = None,
        stripe_event_id: str | None = None,
    ) -> Payment:
        if payment.status == new_status:
            return payment
        validate_transition(payment, new_status)
        return await crud_billing.update_payment_status(
            db,
            payment=payment,
            status=new_status,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_event_id=stripe_event_id,
        )

    async def get_payment_status(
        self,
        db: AsyncSession,  # noqa: ARG004 - kept for symmetry/extensibility
        user: User,
    ) -> PaymentStatusResponse:
        """Return premium status for the authenticated user."""
        return PaymentStatusResponse(
            is_premium=bool(user.is_premium),
            premium_since=user.premium_since,
        )
