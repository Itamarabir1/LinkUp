import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

# ייבוא ה-Singletons של התשתיות
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.redis.client import redis_client
from app.infrastructure.redis.chat_pubsub import redis_chat_pubsub
from app.infrastructure.redis.broadcast import broadcast

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    ניהול מחזור החיים של האפליקציה (Lifespan).
    מבטיח שכל התשתיות (RabbitMQ, Redis Caching, Redis Broadcast)
    עולות ויורדות בצורה מסודרת ואטומיות.
    """

    # --- Startup Phase ---
    logger.info("🚀 [Lifespan] Starting up: Initializing infrastructure...")

    # 1. חיבור ל-RabbitMQ (אופציונלי – Worker צורך; API יכול לרוץ בלי)
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
        # 2. חיבור ל-Redis Client (עבור Caching ו-State)
        await redis_client.connect()
        logger.info("✅ [Lifespan] Redis Client connected")

        # 3. Pub/Sub צ'אט — אותו Redis DB כמו chat-ws (REDIS_CHAT_URL)
        await redis_chat_pubsub.connect()
        logger.info("✅ [Lifespan] Redis Chat Pub/Sub connected")

        # 4. חיבור ל-Redis Broadcast (עבור Real-time Websockets/UI)
        await broadcast.connect()
        logger.info("✅ [Lifespan] Redis Broadcast connected")
        redis_ok = True
    except Exception as e:
        logger.warning(
            "⚠️ [Lifespan] Redis not available (API will start; rate-limit/cache/broadcast disabled): %s",
            e,
        )

    # כאן האפליקציה מתחילה לקבל בקשות (FastAPI Running)
    yield

    # --- Shutdown Phase ---
    logger.info("🛑 [Lifespan] Shutting down: Cleaning up infrastructure...")

    try:
        await rabbit_client.close()
        if redis_ok:
            await redis_client.close()
            await redis_chat_pubsub.close()
            await broadcast.disconnect()
        logger.info("👋 [Lifespan] All infrastructure connections closed safely")
    except Exception as e:
        logger.error(f"⚠️ [Lifespan] Error during shutdown cleanup: {e}")
