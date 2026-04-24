import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Infrastructure singletons
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.redis.broadcast import broadcast
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan: connect/disconnect RabbitMQ and Redis clients cleanly.
    """

    # --- Startup Phase ---
    logger.info("🚀 [Lifespan] Starting up: Initializing infrastructure...")

    # 1. RabbitMQ (optional — workers need it; API can boot without)
    try:
        await rabbit_client.connect()
        logger.info("✅ [Lifespan] RabbitMQ connected")
    except Exception as e:
        logger.warning(
            "⚠️ [Lifespan] RabbitMQ not available (API will start; Outbox/Worker need RabbitMQ): %s",
            e,
        )

    redis_ok = False
    try:
        # 2. Redis cache / general client
        await redis_client.connect()
        logger.info("✅ [Lifespan] Redis Client connected")

        # 3. Chat pub/sub (same Redis DB as chat-ws / REDIS_CHAT_URL)
        await redis_chat_pubsub.connect()
        logger.info("✅ [Lifespan] Redis Chat Pub/Sub connected")

        # 4. Redis broadcast for realtime UI / websockets
        await broadcast.connect()
        logger.info("✅ [Lifespan] Redis Broadcast connected")
        redis_ok = True
    except Exception as e:
        logger.warning(
            "⚠️ [Lifespan] Redis not available (API will start; rate-limit/cache/broadcast disabled): %s",
            e,
        )

    # App serves traffic until shutdown
    yield

    # --- Shutdown Phase ---
    logger.info("🛑 [Lifespan] Shutting down: Cleaning up infrastructure...")

    try:
        if redis_ok:
            await broadcast.disconnect()
            await redis_chat_pubsub.close()
            await redis_client.close()
        await rabbit_client.close()
        logger.info("👋 [Lifespan] All infrastructure connections closed safely")
    except Exception as e:
        logger.error(f"⚠️ [Lifespan] Error during shutdown cleanup: {e}")
