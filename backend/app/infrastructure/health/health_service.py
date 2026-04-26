import logging
from typing import Any

from sqlalchemy import text

from app.db.session import SessionLocal
from app.infrastructure.rabbitmq.client import rabbit_client
from app.infrastructure.redis.client import redis_client

logger = logging.getLogger(__name__)


async def check_liveness() -> dict[str, str]:
    """Process liveness only (no dependency checks)."""
    return {"status": "alive"}


async def check_readiness() -> dict[str, Any]:
    """Dependency readiness: DB + Redis + RabbitMQ."""
    results: dict[str, Any] = {}

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

    # Core services determine health status (not external APIs)
    core_services = ("database", "redis", "rabbitmq")
    results["status"] = "healthy" if all(results.get(s) == "ok" for s in core_services) else "unhealthy"

    # Circuit Breaker state — informational only, does not affect status
    try:
        from app.infrastructure.geo.circuit_breaker import (
            google_directions_cb,
            google_distance_matrix_cb,
            google_geocoding_cb,
        )

        results["circuit_breakers"] = {
            "google_geocoding": google_geocoding_cb.state_name,
            "google_directions": google_directions_cb.state_name,
            "google_distance_matrix": google_distance_matrix_cb.state_name,
        }
    except Exception as e:
        logger.warning("Could not load circuit breaker state: %s", e)

    return results


async def check_health() -> dict[str, Any]:
    """
    Backward-compatibility wrapper.
    Keeps existing /api/v1/health semantics.
    """
    return await check_readiness()
