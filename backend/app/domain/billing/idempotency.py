import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions.billing import IdempotencyMismatchError
from app.domain.billing.crud import crud_billing


@dataclass(slots=True)
class IdempotencyCachedResponse:
    response_body: dict
    status_code: int


def make_checkout_fingerprint(*, user_id: UUID, currency: str) -> str:
    raw = f"{user_id}|/billing/checkout|{currency.lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdempotencyManager:
    async def check(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        client_key: str,
        endpoint: str,
        request_fingerprint: str,
    ) -> IdempotencyCachedResponse | None:
        existing = await crud_billing.get_idempotency_key(
            db,
            user_id=user_id,
            client_key=client_key,
            endpoint=endpoint,
        )
        if not existing:
            return None
        if existing.request_fingerprint != request_fingerprint:
            raise IdempotencyMismatchError()
        if existing.expires_at <= datetime.now(UTC):
            return None
        body = existing.response_body if isinstance(existing.response_body, dict) else json.loads(existing.response_body)
        return IdempotencyCachedResponse(response_body=body, status_code=int(existing.status_code))

    async def store(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        client_key: str,
        endpoint: str,
        request_fingerprint: str,
        response_body: dict,
        status_code: int,
        ttl_hours: int | None = None,
    ) -> None:
        ttl = ttl_hours if ttl_hours is not None else settings.BILLING_IDEMPOTENCY_TTL_HOURS
        expires_at = datetime.now(UTC) + timedelta(hours=ttl)
        await crud_billing.upsert_idempotency_key(
            db,
            user_id=user_id,
            client_key=client_key,
            endpoint=endpoint,
            request_fingerprint=request_fingerprint,
            response_body=response_body,
            status_code=status_code,
            expires_at=expires_at,
        )

    async def cleanup_expired(self, db: AsyncSession) -> int:
        return await crud_billing.delete_expired_idempotency_keys(db, older_than=datetime.now(UTC))
