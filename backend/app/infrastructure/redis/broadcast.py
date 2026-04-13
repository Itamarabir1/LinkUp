import logging

from broadcaster import Broadcast

from app.core.config import settings
from app.core.exceptions.infrastructure import InfrastructureError

logger = logging.getLogger(__name__)


class RedisBroadcast:
    def __init__(self):
        # Uses settings.REDIS_URL
        self.engine = Broadcast(settings.REDIS_URL)

    async def connect(self):
        await self.engine.connect()
        logger.info("✅ Redis Broadcast (Pub/Sub) initialized.")

    async def disconnect(self):
        await self.engine.disconnect()
        logger.info("⚠️ Redis Broadcast connection closed.")

    async def publish(self, channel: str, message: str):
        """Method invoked by InAppProvider."""
        try:
            await self.engine.publish(channel=channel, message=message)
        except Exception as e:
            raise InfrastructureError(f"Broadcast failed on {channel}", detail=str(e))

    def subscribe(self, channel: str):
        """
        Returns the broadcaster context manager.
        Enables: async with broadcast.subscribe(...)
        """
        return self.engine.subscribe(channel=channel)


# Process-wide singleton
broadcast = RedisBroadcast()
