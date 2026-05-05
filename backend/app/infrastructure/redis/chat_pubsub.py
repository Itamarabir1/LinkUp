"""
Pub/Sub for chat channels in Redis — must use the same DB index as chat-ws (REDIS_CHAT_URL / REDIS_CHAT_DB).
Publishing to DB 0 while chat-ws listens on DB 1 breaks real-time delivery.
"""

import logging

import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisChatPubSub:
    """Dedicated connection to REDIS_CHAT_URL — chat:conversation:*, user:*:events (and other DB1 pub/sub used with chat-ws)."""

    def __init__(self):
        self.client: redis.Redis | None = None
        self.pool: redis.ConnectionPool | None = None
        self.sentinel: Sentinel | None = None

    async def connect(self) -> None:
        if self.client is not None:
            return
        if settings.REDIS_SENTINEL_HOST:
            self.sentinel = Sentinel(
                [(settings.REDIS_SENTINEL_HOST, settings.REDIS_SENTINEL_PORT)],
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
            self.client = self.sentinel.master_for(
                settings.REDIS_MASTER_NAME,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_CHAT_DB,
                decode_responses=True,
            )
        else:
            self.pool = redis.ConnectionPool.from_url(
                settings.REDIS_CHAT_URL,
                decode_responses=True,
                max_connections=10,
            )
            self.client = redis.Redis(connection_pool=self.pool)
        logger.info(
            "✅ Redis Chat Pub/Sub connected (DB for chat-ws alignment): %s",
            settings.REDIS_CHAT_URL.split("@")[-1] if "@" in settings.REDIS_CHAT_URL else settings.REDIS_CHAT_URL,
        )

    async def publish(self, channel: str, message: str) -> int:
        if self.client is None:
            logger.warning("Redis Chat Pub/Sub not connected, skip publish to %s", channel)
            return 0
        try:
            return await self.client.publish(channel, message)
        except Exception as e:
            logger.warning("Redis chat publish failed (channel=%s): %s", channel, e)
            return 0

    async def close(self) -> None:
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
        self.client = None
        self.pool = None
        self.sentinel = None
        logger.info("⚠️ Redis Chat Pub/Sub closed.")


redis_chat_pubsub = RedisChatPubSub()
