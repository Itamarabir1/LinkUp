"""
Redis Pub/Sub — publish to channels.
Used for real-time chat: Python publishes, WS server (Go) subscribes.
Separate from redis/client.py which handles cache and rate limiting.
"""

import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisPubSub:
    """Dedicated Redis connection for Pub/Sub (publish)."""

    def __init__(self):
        self.client: redis.Redis | None = None
        self.pool: redis.ConnectionPool | None = None

    async def connect(self) -> None:
        if self.client is not None:
            return
        self.pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=10,
        )
        self.client = redis.Redis(connection_pool=self.pool)
        logger.info("✅ Redis Pub/Sub (publish) initialized.")

    async def publish(self, channel: str, message: str) -> int:
        """
        Publishes a message to a channel. Every subscriber receives it.
        Returns the number of clients that received the message (0 if none).
        """
        if self.client is None:
            logger.warning("Redis Pub/Sub not connected, skip publish to %s", channel)
            return 0
        try:
            return await self.client.publish(channel, message)
        except Exception as e:
            logger.warning("Redis publish failed (channel=%s): %s", channel, e)
            return 0

    async def close(self) -> None:
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
        self.client = None
        self.pool = None
        logger.info("⚠️ Redis Pub/Sub connection closed.")


redis_pubsub = RedisPubSub()
