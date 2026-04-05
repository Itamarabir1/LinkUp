import logging

from sqlalchemy import text

from app.db.session import SessionLocal
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)


async def check_health() -> dict:
    results: dict[str, str] = {}

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        results["database"] = "ok"
    except Exception as e:
        logger.error("Health check DB failed: %s", e)
        results["database"] = "error"

    try:
        if redis_client.client is None:
            await redis_client.connect()
        await redis_client.client.ping()
        results["redis"] = "ok"
    except Exception as e:
        logger.error("Health check Redis failed: %s", e)
        results["redis"] = "error"

    try:
        if rabbit_client.is_connected():
            results["rabbitmq"] = "ok"
        else:
            results["rabbitmq"] = "error"
    except Exception as e:
        logger.error("Health check RabbitMQ failed: %s", e)
        results["rabbitmq"] = "error"

    results["status"] = "healthy" if all(v == "ok" for v in results.values()) else "unhealthy"
    return results
