# app/api/v1/api_router.py
from fastapi import APIRouter

from app.api.v1.routers.rides import router as rides_router
from app.api.v1.routers.passengers import (
    router as passenger_router,
    passenger_rides_router,
)
from app.api.v1.routers.bookings import router as bookings_router
from app.api.v1.routers.users import router as user_router
from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.geo import router as geo_router
from app.api.v1.routers.chat import router as chat_router
from app.api.websockets.notifications import router as notifications_ws_router

api_router = APIRouter()

api_router.include_router(rides_router, prefix="/rides", tags=["Rides"])
api_router.include_router(passenger_router, prefix="/passenger", tags=["Passenger"])
api_router.include_router(
    passenger_rides_router, prefix="/passenger", tags=["Passenger"]
)
api_router.include_router(bookings_router, prefix="/bookings", tags=["Bookings"])
api_router.include_router(user_router, prefix="/users", tags=["Users"])
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(geo_router, prefix="/geo", tags=["Geo"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(
    notifications_ws_router, prefix="/notifications", tags=["Notifications"]
)

# Groups last to avoid circular import (User <-> Group via app.db.models)
from app.api.v1.routers.groups import router as groups_router
api_router.include_router(groups_router, prefix="/groups", tags=["Groups"])