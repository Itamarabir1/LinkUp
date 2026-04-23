import logging
from dataclasses import dataclass

import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.core.exceptions.infrastructure import InfrastructureError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BroadcastEvent:
    message: str


class RedisSubscriber:
    def __init__(self, pubsub: redis.client.PubSub, channel: str):
        self._pubsub = pubsub
        self._channel = channel
        self._closed = False

    async def __aenter__(self):
        await self._pubsub.subscribe(self._channel)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._cleanup()
        return False

    def __aiter__(self):
        return self

    async def __anext__(self):
        while True:
            if self._closed:
                raise StopAsyncIteration
            try:
                msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            except WebSocketDisconnect:
                await self._cleanup()
                raise StopAsyncIteration
            except Exception:
                await self._cleanup()
                raise
            if msg is None:
                continue
            data = msg.get("data")
            if data is None:
                continue
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return BroadcastEvent(message=str(data))

    async def _cleanup(self):
        if self._closed:
            return
        self._closed = True
        try:
            await self._pubsub.unsubscribe(self._channel)
        except Exception:
            logger.debug("Redis subscriber unsubscribe skipped", exc_info=True)
        try:
            await self._pubsub.close()
        except Exception:
            logger.debug("Redis subscriber close skipped", exc_info=True)


class RedisBroadcast:
    def __init__(self):
        self.client: redis.Redis | None = None
        self.pool: redis.ConnectionPool | None = None
        self.sentinel: Sentinel | None = None

    async def connect(self):
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
                max_connections=20,
            )
            self.client = redis.Redis(connection_pool=self.pool)
        logger.info("✅ Redis Broadcast (Pub/Sub) initialized.")

    async def disconnect(self):
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()
        self.client = None
        self.pool = None
        self.sentinel = None
        logger.info("⚠️ Redis Broadcast connection closed.")

    async def publish(self, channel: str, message: str):
        """Method invoked by InAppProvider."""
        try:
            if self.client is None:
                await self.connect()
            await self.client.publish(channel=channel, message=message)
        except Exception as e:
            raise InfrastructureError(f"Broadcast failed on {channel}", detail=str(e))

    def subscribe(self, channel: str):
        """
        Returns an async context manager with event.message API.
        Enables: async with broadcast.subscribe(...)
        """
        if self.client is None:
            raise InfrastructureError("Broadcast is not connected")
        return RedisSubscriber(self.client.pubsub(), channel)


# Process-wide singleton
broadcast = RedisBroadcast()
