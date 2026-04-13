# app/domain/auth/verification_service.py
import hmac
import logging
import secrets

from app.core.exceptions.auth import (
    InvalidVerificationCodeError,
    VerificationCodeExpiredError,
)
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.keys import OTP_VERIFICATION_TTL, get_otp_verification_key

logger = logging.getLogger(__name__)


class VerificationService:
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        return "".join(secrets.choice("0123456789") for _ in range(length))

    async def create_verification_event(self, user_id: str, event_name: str) -> str:
        code = self.generate_otp()
        redis_key = get_otp_verification_key(user_id, event_name)
        # Generic store for all verification event types
        await redis_client.save(key=redis_key, data=code, expire=OTP_VERIFICATION_TTL)
        await redis_client.client.delete(f"otp_attempts:{user_id}:{event_name}")
        return code

    async def verify_otp(self, user_id: str, event_name: str, input_code: str) -> None:
        """Verifies the OTP code and raises the appropriate error on failure."""
        redis_key = get_otp_verification_key(user_id, event_name)
        attempts_key = f"otp_attempts:{user_id}:{event_name}"

        # Code must exist in Redis
        stored_code = await redis_client.get(redis_key)
        if not stored_code:
            raise VerificationCodeExpiredError()

        # Attempt counter — max 5 before invalidating
        attempts = await redis_client.client.incr(attempts_key)
        if attempts == 1:
            await redis_client.client.expire(attempts_key, OTP_VERIFICATION_TTL)
        if attempts > 5:
            await redis_client.delete(redis_key)
            logger.warning("OTP brute-force detected: user=%s event=%s", user_id, event_name)
            raise VerificationCodeExpiredError()

        # Constant-time compare
        if not hmac.compare_digest(str(stored_code), str(input_code)):
            raise InvalidVerificationCodeError()

        # Success — delete code and counter
        await redis_client.delete(redis_key)
        await redis_client.client.delete(attempts_key)


verification_service = VerificationService()
