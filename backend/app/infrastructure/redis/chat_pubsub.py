"""
Pub/Sub לערוצי צ'אט ב-Redis — חייב להיות אותו מספר DB כמו chat-ws (REDIS_CHAT_URL / REDIS_CHAT_DB).
פרסום ל-DB 0 כש-chat-ws מאזין ב-DB 1 גורם להודעות שלא מגיעות בזמן אמת.
"""

import logging

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisChatPubSub:
    """חיבור ייעודי ל-REDIS_CHAT_URL — chat:conversation:*, chat:notification:*, user:*:events"""

    def __init__(self):
        self.client: redis.Redis | None = None
        self.pool: redis.ConnectionPool | None = None

    async def connect(self) -> None:
        if self.client is not None:
            return
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
        logger.info("⚠️ Redis Chat Pub/Sub closed.")


redis_chat_pubsub = RedisChatPubSub()
