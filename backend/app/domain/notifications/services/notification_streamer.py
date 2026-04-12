import logging
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

# Architectural fix: import the Bus instead of Redis directly
from app.infrastructure.websocket_bus import ws_infra

logger = logging.getLogger(__name__)


class NotificationStreamer:
    """
    Streams real-time data from infrastructure (Bus) to the physical pipe (WebSocket).
    """

    async def stream_user_notifications(self, websocket: WebSocket, user_id: UUID | str | int):
        """
        Subscribes to the user channel and streams messages until disconnect.
        """
        channel_name = f"user_{user_id}"

        try:
            # Step 1: get subscriber from infrastructure (ws_infra)
            # await because get_subscriber is async
            subscriber_ctx = await ws_infra.get_subscriber(channel_name)

            async with subscriber_ctx as subscriber:
                logger.info(f"🔌 WebSocket subscription active for: {channel_name}")

                # Step 2: streaming loop (event loop)
                async for event in subscriber:
                    try:
                        # Send message to client as text
                        await websocket.send_text(event.message)

                    except (WebSocketDisconnect, ConnectionResetError):
                        # Normal disconnect (closed tab / lost connection)
                        logger.info(f"👋 User {user_id} disconnected from WebSocket.")
                        break

                    except Exception as send_error:
                        logger.error(
                            "Failed to push WebSocket message to user %s: %s",
                            user_id,
                            send_error,
                            exc_info=True,
                        )
                        break

        except Exception as e:
            logger.error(
                "Critical notification streamer error for user %s: %s",
                user_id,
                e,
                exc_info=True,
            )

        finally:
            # Step 3: resource cleanup always runs here
            logger.debug(f"🧹 Cleaned up stream resources for user {user_id}")


# Singleton instance for the Router
notification_streamer = NotificationStreamer()
