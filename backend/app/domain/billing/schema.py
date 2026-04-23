from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.domain.billing.model import PaymentStatus


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PaymentStatusResponse(BaseModel):
    is_premium: bool
    premium_since: datetime | None = None


class PaymentRead(BaseModel):
    payment_id: UUID
    user_id: UUID
    stripe_payment_intent_id: str | None
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        return v.lower()

    model_config = {"from_attributes": True}
