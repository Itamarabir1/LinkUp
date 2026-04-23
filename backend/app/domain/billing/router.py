import logging

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_billing_service
from app.db.session import get_db
from app.domain.billing.crud import crud_billing
from app.domain.billing.schema import CheckoutResponse, PaymentRead, PaymentStatusResponse
from app.domain.billing.service import BillingService
from app.domain.users.model import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Billing"])


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_checkout(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Create a Stripe Checkout Session for premium upgrade."""
    return await billing_service.create_checkout_session(db, user=current_user)


@router.get("/status", response_model=PaymentStatusResponse)
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
):
    """Return whether the authenticated user is premium."""
    return await billing_service.get_payment_status(db, user=current_user)


@router.get("/payments", response_model=list[PaymentRead])
async def get_my_payments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return payment history for the authenticated user."""
    return await crud_billing.get_user_payments(db, user_id=current_user.user_id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    billing_service: BillingService = Depends(get_billing_service),
):
    """
    Stripe webhook endpoint.
    No auth - Stripe calls this directly.
    Signature verified inside handle_webhook.
    """
    payload = await request.body()
    stripe_signature = request.headers.get("Stripe-Signature", "")
    return await billing_service.handle_webhook(
        db,
        payload=payload,
        stripe_signature=stripe_signature,
    )
