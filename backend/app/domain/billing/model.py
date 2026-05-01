import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Payment(Base):
    """
    Payment entity - records every Stripe payment attempt.
    source of truth for billing; users.is_premium is a cache.
    """

    __tablename__ = "payments"

    payment_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    # Stripe identifiers
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True)
    stripe_session_id = Column(String(255), unique=True, nullable=True)
    stripe_event_id = Column(String(255), unique=True, nullable=True)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False, default="ils")
    status = Column(
        Enum(
            PaymentStatus,
            name="payment_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
        server_default=PaymentStatus.PENDING.value,
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    user = relationship("User", back_populates="payments")

    __table_args__ = (
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_status", "status"),
    )

    def __repr__(self):
        return f"<Payment(id={self.payment_id}, user={self.user_id}, status={self.status})>"


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_key = Column(String(128), nullable=False)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    endpoint = Column(String(64), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)
    response_body = Column(JSONB, nullable=False)
    status_code = Column(Integer, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "client_key", "endpoint", name="uq_idem_user_client_endpoint"),
        Index("idx_idempotency_expires_at", "expires_at"),
    )
