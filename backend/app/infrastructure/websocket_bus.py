# app/infrastructure/websocket_bus.py
import logging

# Import Redis infra directly (avoid circular deps)
from app.infrastructure.redis.broadcast import broadcast

logger = logging.getLogger(__name__)


class WebSocketInfrastructure:
    """
    Thin adapter from Redis pub/sub to domain notification streaming.
    """

    @staticmethod
    async def get_subscriber(channel_name: str):
        """
        Return Redis subscribe context manager for channel_name.
        """
        try:
            # Return async context manager as-is
            return broadcast.subscribe(channel=channel_name)
        except Exception as e:
            logger.error(f"❌ Failed to create subscriber for channel {channel_name}: {e}")
            # Could wrap in LinkupError for consistent API errors
            raise


# Singleton export
ws_infra = WebSocketInfrastructure()
