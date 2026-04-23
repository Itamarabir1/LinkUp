import asyncio
import logging
from decimal import Decimal
from uuid import UUID

import stripe
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions.billing import (
    CheckoutSessionError,
    PaymentAlreadyExistsError,
    StripeWebhookError,
    UserAlreadyPremiumError,
)
from app.domain.billing.crud import crud_billing
from app.domain.billing.model import Payment, PaymentStatus
from app.domain.billing.schema import CheckoutResponse, PaymentStatusResponse
from app.domain.users.crud import crud_user
from app.domain.users.model import User

logger = logging.getLogger(__name__)

# Premium plan price - set in Stripe Dashboard, store ID in env
PREMIUM_PRICE_ILS = Decimal("29.90")
PREMIUM_AMOUNT = int(PREMIUM_PRICE_ILS * 100)  # Stripe uses agorot


class BillingService:
    @staticmethod
    async def create_checkout_session(
        db: AsyncSession,
        user: User,
    ) -> CheckoutResponse:
        """
        Create a Stripe Checkout Session for premium upgrade.
        Creates or reuses stripe_customer_id on the user.
        """
        if user.is_premium:
            raise UserAlreadyPremiumError()

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            # 1. Get or create Stripe customer
            if not getattr(user, "stripe_customer_id", None):
                customer = await asyncio.to_thread(
                    stripe.Customer.create,
                    email=user.email,
                    name=user.full_name,
                    metadata={"user_id": str(user.user_id)},
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
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                customer=stripe_customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "ils",
                            "unit_amount": PREMIUM_AMOUNT,
                            "product_data": {
                                "name": "LinkUp Premium",
                                "description": "גישה מלאה לכל פיצ'רי LinkUp",
                            },
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/payment/cancel",
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

            logger.info(
                "Checkout session created for user=%s session=%s",
                user.user_id,
                session.id,
            )
            return CheckoutResponse(checkout_url=session.url, session_id=session.id)

        except IntegrityError as e:
            await db.rollback()
            logger.warning("Duplicate payment record for checkout session: %s", e)
            raise PaymentAlreadyExistsError() from e
        except stripe.StripeError as e:
            await db.rollback()
            logger.error("Stripe error creating checkout: %s", e)
            raise CheckoutSessionError() from e

    @staticmethod
    async def handle_webhook(
        db: AsyncSession,
        payload: bytes,
        stripe_signature: str,
    ) -> dict:
        """
        Handle Stripe webhook.
        Verifies signature, processes checkout.session.completed.
        Idempotent - safe to call multiple times with same event.
        """
        stripe.api_key = settings.STRIPE_SECRET_KEY

        if not stripe_signature:
            raise StripeWebhookError()

        # 1. Verify signature
        try:
            event = await asyncio.to_thread(
                stripe.Webhook.construct_event,
                payload,
                stripe_signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except stripe.SignatureVerificationError as e:
            logger.warning("Stripe webhook signature verification failed: %s", e)
            raise StripeWebhookError() from e
        except Exception as e:
            logger.warning("Stripe webhook invalid payload/signature: %s", e)
            raise StripeWebhookError() from e

        # 2. Handle event types
        if event.get("type") == "checkout.session.completed":
            await BillingService._handle_checkout_completed(db, event)

        return {"status": "ok"}

    @staticmethod
    async def _handle_checkout_completed(db: AsyncSession, event: dict) -> None:
        """
        Mark payment as succeeded and upgrade user to premium.
        Idempotent at two levels:
        - event-level: stripe_event_id
        - payment-level: stripe_payment_intent_id
        """
        stripe_event_id = event.get("id")
        session = event.get("data", {}).get("object", {})
        stripe_session_id = session.get("id")
        stripe_payment_intent_id = session.get("payment_intent")
        user_id = session.get("metadata", {}).get("user_id")

        if not user_id or not stripe_payment_intent_id:
            logger.warning("Webhook missing user_id or payment_intent: %s", session)
            return

        # Event-level idempotency
        if stripe_event_id:
            existing_event = await crud_billing.get_by_event_id(db, stripe_event_id)
            if existing_event:
                logger.info("Webhook event already processed event_id=%s", stripe_event_id)
                return

        # Payment-level idempotency
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

        try:
            # Update payment record
            payment = await crud_billing.get_by_session_id(db, stripe_session_id)
            if payment:
                await crud_billing.update_payment_status(
                    db,
                    payment=payment,
                    status=PaymentStatus.SUCCEEDED,
                    stripe_payment_intent_id=stripe_payment_intent_id,
                    stripe_event_id=stripe_event_id,
                )
            else:
                amount_decimal = Decimal(str(session.get("amount_total", 0))) / Decimal("100")
                payment = Payment(
                    user_id=UUID(user_id),
                    amount=amount_decimal,
                    currency=str(session.get("currency", "ils")).lower(),
                    stripe_session_id=stripe_session_id,
                    stripe_payment_intent_id=stripe_payment_intent_id,
                    stripe_event_id=stripe_event_id,
                    status=PaymentStatus.SUCCEEDED,
                )
                db.add(payment)
                await db.flush()

            # Mark user as premium (no-op if already premium)
            user = await crud_user.get_by_id(db, UUID(user_id))
            if user and not user.is_premium:
                await crud_user.mark_as_premium(db, user=user)

            await db.commit()
            logger.info("User %s upgraded to premium", user_id)

        except IntegrityError as e:
            await db.rollback()
            logger.warning("Duplicate Stripe identifiers while handling webhook: %s", e)
            raise PaymentAlreadyExistsError() from e
        except Exception as e:
            await db.rollback()
            logger.error("Failed to handle checkout.completed: %s", e)
            raise

    @staticmethod
    async def get_payment_status(
        db: AsyncSession,  # noqa: ARG004 - kept for symmetry/extensibility
        user: User,
    ) -> PaymentStatusResponse:
        """Return premium status for the authenticated user."""
        return PaymentStatusResponse(
            is_premium=bool(user.is_premium),
            premium_since=user.premium_since,
        )
