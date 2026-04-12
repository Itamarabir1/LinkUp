import logging
from typing import Any
from uuid import UUID

from app.domain.rides.services.maps_service import maps_service

# TODO: dispatch function does not exist — EventDispatcher.dispatch is a method, not a module-level function
from app.infrastructure.events.dispatcher.dispatcher import dispatch

from app.core.exceptions import InfrastructureError
from app.core.exceptions.infrastructure import WorkerTaskFailed
from app.db.session import SessionLocal
from app.domain.rides.crud import crud_ride

logger = logging.getLogger(__name__)


async def handle_map_tasks(payload: dict[str, Any], routing_key: str):
    """
    Routes map tasks by routing_key.
    Example key: ride.maps.calculate_route
    """
    if routing_key == "ride.maps.calculate_route":
        await calculate_ride_route_task(payload)


async def calculate_ride_route_task(data: dict[str, Any]):
    """
    Heavy task: call Google Maps, update DB, dispatch completion event.
    """
    ride_id_raw = data.get("ride_id")
    origin = data.get("origin")
    destination = data.get("destination")

    if not all([ride_id_raw, origin, destination]):
        logger.error("Missing data for route calculation: %s", data)
        raise WorkerTaskFailed(message="חסרים נתונים לחישוב מסלול")

    ride_id = UUID(str(ride_id_raw))
    logger.info(f"🗺️ Calculating route for Ride {ride_id}...")

    # Use context manager for DB lifecycle
    with SessionLocal() as db:
        try:
            # 1. Call external API (slow)
            route_result = await maps_service.get_directions(origin, destination)

            # 2. Persist to database
            crud_ride.update_route_details(db, ride_id=ride_id, route_data=route_result)

            logger.info(f"✅ Route updated for Ride {ride_id}")

            # 3. No WebSocket from here — dispatch event that route is ready
            user_id_raw = data.get("user_id")
            await dispatch(
                "RIDE_ROUTE_READY",
                {
                    "ride_id": str(ride_id),
                    "user_id": str(user_id_raw) if user_id_raw is not None else None,
                    "distance": route_result.get("distance"),
                    "duration": route_result.get("duration"),
                },
            )

        except InfrastructureError as e:
            # InfrastructureError (e.g. Google Maps down)
            logger.error(f"⚠️ Maps API failure for ride {ride_id}: {e.message}")
            raise  # RabbitMQ will retry after a delay

        except Exception as e:
            logger.error("Unexpected error in ride task: %s", e, exc_info=True)
            raise WorkerTaskFailed() from e
