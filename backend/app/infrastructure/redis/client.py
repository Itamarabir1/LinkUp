import json
import logging

import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions.infrastructure import RedisUnavailable

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.client: redis.Redis = None
        self.pool: redis.ConnectionPool = None

    async def connect(self):
        if not self.client:
            self.pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True, max_connections=20)
            self.client = redis.Redis(connection_pool=self.pool)
            logger.info("✅ Redis Client (Caching) initialized.")

    async def save(self, key: str, data: any, expire: int = 3600):
        try:
            if self.client is None:
                await self.connect()
            # TTL seconds for SETEX; None → default 3600
            if expire is None:
                expire = 3600
            expire = max(1, int(expire))
            val = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
            await self.client.setex(key, expire, val)
        except Exception as e:
            logger.error("Redis SAVE failed key=%s: %s", key, e, exc_info=True)
            raise RedisUnavailable() from e

    async def get(self, key: str):
        try:
            if self.client is None:
                await self.connect()
            data = await self.client.get(key)
            if not data:
                return None
            try:
                return json.loads(data)
            except Exception as parse_err:
                logger.warning("Redis GET value is not JSON key=%s: %s", key, parse_err)
                return data
        except Exception as e:
            logger.error("Redis GET failed key=%s: %s", key, e, exc_info=True)
            raise RedisUnavailable() from e

    async def close(self):
        if self.client:
            await self.client.close()
            await self.pool.disconnect()
            logger.info("⚠️ Redis Client connection closed.")

    async def delete(self, key: str) -> bool:
        """
        Deletes a key from the cache.
        Returns True if the key was removed, False if it did not exist.
        """
        try:
            result = await self.client.delete(key)
            logger.debug("Redis DELETE: %s (Result: %s)", key, result)
            return bool(result)
        except Exception as e:
            logger.error("Redis DELETE failed key=%s: %s", key, e, exc_info=True)
            raise RedisUnavailable() from e

    async def rate_limit_check(self, key: str, window_seconds: int, max_count: int) -> bool:
        """
        Rate limit check: increments a counter in Redis, returns True if allowed, False if exceeded.
        If Redis is disconnected or an error occurs — returns True (fail open).
        """
        if not self.client:
            logger.warning("Rate limit skipped — Redis not connected | key=%s", key)
            return True
        try:
            count = await self.client.incr(key)
            if count == 1:
                await self.client.expire(key, window_seconds)
            return count <= max_count
        except Exception as e:
            logger.warning(
                "Rate limit check failed — fail open (Redis unavailable) | key=%s error=%s",
                key,
                e,
            )
            return True

    async def add_to_denylist(self, jti: str, ttl_seconds: int) -> None:
        """Store denylist:{jti} with TTL. Fail-open: log errors, do not raise."""
        try:
            if self.client is None:
                await self.connect()
            ttl_seconds = max(1, int(ttl_seconds))
            await self.client.setex(f"denylist:{jti}", ttl_seconds, "1")
        except Exception as e:
            logger.warning("Redis DENYLIST add failed jti=%s: %s", jti, e)

    async def is_denied(self, jti: str) -> bool:
        """Return True if jti is denied. Fail-open: False if Redis fails."""
        try:
            if self.client is None:
                await self.connect()
            return bool(await self.client.exists(f"denylist:{jti}"))
        except Exception as e:
            logger.warning("Redis DENYLIST check failed jti=%s: %s", jti, e)
            return False

    async def idempotency_try_begin(
        self,
        key: str,
        fingerprint: str,
        ttl_processing: int = 30,
    ) -> str:
        """
        Atomic claim with SET NX.
        Returns: 'leader' | 'in_progress' | 'mismatch' | 'completed:<json>'
        key format: idempotency:request_ride:{user_id}:{client_key}
        fingerprint: SHA-256 of canonical request body
        """
        finger_key = f"{key}:fingerprint"

        def _fp_mismatch(stored_finger: str | None) -> bool:
            return bool(stored_finger and stored_finger != fingerprint)

        try:
            if self.client is None:
                await self.connect()

            existing = await self.client.get(key)
            if existing == "PROCESSING":
                stored_finger = await self.client.get(finger_key)
                if _fp_mismatch(stored_finger):
                    return "mismatch"
                return "in_progress"

            if existing:
                stored_finger = await self.client.get(finger_key)
                if _fp_mismatch(stored_finger):
                    return "mismatch"
                return f"completed:{existing}"

            won = await self.client.set(key, "PROCESSING", ex=ttl_processing, nx=True)
            if not won:
                existing_after = await self.client.get(key)
                if existing_after and existing_after != "PROCESSING":
                    stored_finger = await self.client.get(finger_key)
                    if _fp_mismatch(stored_finger):
                        return "mismatch"
                    return f"completed:{existing_after}"
                if existing_after == "PROCESSING":
                    stored_finger = await self.client.get(finger_key)
                    if _fp_mismatch(stored_finger):
                        return "mismatch"
                    return "in_progress"
                return "in_progress"

            await self.client.set(finger_key, fingerprint, ex=ttl_processing)
            return "leader"

        except Exception as e:
            logger.warning(
                "Redis idempotency_try_begin failed key=%s: %s — fail open",
                key,
                e,
            )
            return "leader"

    async def idempotency_set_result(self, key: str, json_result: str, ttl: int = 300) -> None:
        """Store successful result JSON. Extends TTL to result window."""
        finger_key = f"{key}:fingerprint"
        try:
            if self.client is None:
                await self.connect()
            await self.client.set(key, json_result, ex=ttl)
            await self.client.expire(finger_key, ttl)
        except Exception as e:
            logger.warning("Redis idempotency_set_result failed key=%s: %s", key, e)

    async def idempotency_delete(self, key: str) -> None:
        """Delete lock on failure so client can retry."""
        finger_key = f"{key}:fingerprint"
        try:
            if self.client is None:
                await self.connect()
            await self.client.delete(key, finger_key)
        except Exception as e:
            logger.warning("Redis idempotency_delete failed key=%s: %s", key, e)


redis_client = RedisClient()
