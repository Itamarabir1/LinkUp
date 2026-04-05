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
            # expire בשניות (Redis SETEX); ערך 0 או None – משתמשים בברירת מחדל
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
        מוחק מפתח מה-Cache.
        מחזיר True אם המפתח נמחק, False אם לא היה קיים.
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
        בודק rate limit: מגדיל מונה ב-Redis, מחזיר True אם מותר, False אם חרג.
        אם Redis לא מחובר או שגיאה – מחזיר True (fail open).
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


redis_client = RedisClient()
