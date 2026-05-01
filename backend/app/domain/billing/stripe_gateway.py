import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import stripe

from app.core.config import settings
from app.core.exceptions.billing import CheckoutSessionError, StripeWebhookError


@dataclass(slots=True)
class StripeCustomerDTO:
    id: str


@dataclass(slots=True)
class StripeSessionDTO:
    id: str
    url: str | None
    status: str | None
    payment_status: str | None
    payment_intent: str | None
    currency: str | None
    amount_total: int | None
    metadata: dict[str, Any]


@dataclass(slots=True)
class StripeEventDTO:
    id: str | None
    type: str
    data_object: dict[str, Any]


class StripeGateway:
    def __init__(self, *, secret_key: str | None = None, webhook_secret: str | None = None) -> None:
        self.secret_key = secret_key or settings.STRIPE_SECRET_KEY
        self.webhook_secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET
        stripe.api_key = self.secret_key

    async def create_customer(self, *, email: str, name: str, user_id: str) -> StripeCustomerDTO:
        try:
            customer = await asyncio.to_thread(
                stripe.Customer.create,
                email=email,
                name=name,
                metadata={"user_id": user_id},
            )
            return StripeCustomerDTO(id=customer.id)
        except stripe.StripeError as exc:
            raise CheckoutSessionError() from exc

    async def create_checkout_session(self, *, customer_id: str, amount: Decimal, metadata: dict[str, str]) -> StripeSessionDTO:
        unit_amount = int(amount * 100)
        try:
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "ils",
                            "unit_amount": unit_amount,
                            "product_data": {
                                "name": "LinkUp Premium",
                                "description": "גישה מלאה לכל פיצ'רי LinkUp",
                            },
                        },
                        "quantity": 1,
                    },
                ],
                mode="payment",
                phone_number_collection={"enabled": False},
                locale="auto",
                custom_text={"submit": {"message": "לאחר התשלום תקבל גישה מיידית לכל פיצ'רי LinkUp Premium"}},
                payment_intent_data={
                    "description": "LinkUp Premium - גישה מלאה לכל פיצ'רי LinkUp",
                    "metadata": metadata,
                },
                success_url=f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.FRONTEND_URL}/payment/cancel",
                metadata=metadata,
            )
            return self._session_to_dto(session)
        except stripe.StripeError as exc:
            raise CheckoutSessionError() from exc

    async def retrieve_session(self, session_id: str) -> StripeSessionDTO:
        try:
            session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
            return self._session_to_dto(session)
        except stripe.StripeError as exc:
            raise CheckoutSessionError() from exc

    async def construct_webhook_event(self, *, payload: bytes, signature: str) -> StripeEventDTO:
        if not signature:
            raise StripeWebhookError()
        try:
            event = await asyncio.to_thread(
                stripe.Webhook.construct_event,
                payload,
                signature,
                self.webhook_secret,
            )
            return StripeEventDTO(
                id=event.get("id"),
                type=event.get("type", "unknown"),
                data_object=event.get("data", {}).get("object", {}),
            )
        except stripe.SignatureVerificationError as exc:
            raise StripeWebhookError() from exc
        except Exception as exc:  # noqa: BLE001
            raise StripeWebhookError() from exc

    @staticmethod
    def _session_to_dto(session: Any) -> StripeSessionDTO:
        metadata = dict(getattr(session, "metadata", {}) or {})
        return StripeSessionDTO(
            id=session.id,
            url=getattr(session, "url", None),
            status=getattr(session, "status", None),
            payment_status=getattr(session, "payment_status", None),
            payment_intent=getattr(session, "payment_intent", None),
            currency=getattr(session, "currency", None),
            amount_total=getattr(session, "amount_total", None),
            metadata=metadata,
        )
